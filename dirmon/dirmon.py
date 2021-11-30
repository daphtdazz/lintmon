import atexit
import logging
import os
from queue import SimpleQueue
from signal import SIGTERM
from subprocess import Popen, PIPE
from threading import Thread

from .monitor_session import MonitorSession
from .settings import DEFAULT_IGNORED_DIRECTORY_NAMES
from .utils import lf


log = logging.getLogger(__name__)


class Dirmon:
    @property
    def badges(self):
        return ''.join(sess.badge for sess in self.sessions)

    def __init__(self, config):
        self.config = config
        self.sessions = []
        self.fswatch_proc = None
        self.files_queue = None

    def load_latest_sessions(self):
        new_sessions = self.new_sessions([])
        for sess in new_sessions:
            sess.skip()

        self.sessions = new_sessions

    def start_fswatch(self):
        excluded_dir_paths_options = [
            arg
            for dirpattern in (f'{dname}/' for dname in DEFAULT_IGNORED_DIRECTORY_NAMES)
            for arg in ['--exclude', dirpattern]
        ]

        args = ['fswatch', '--extended', *excluded_dir_paths_options, os.curdir]
        log.info('Starting fswatch')
        log.debug('Args: %s', args)
        self.files_queue = SimpleQueue()
        self.fswatch = Popen(args, stdout=PIPE, stderr=PIPE, encoding='utf8',)
        atexit.register(self.fswatch.terminate)

        # non-daemon thread doesn't need to be joined or terminated: will exit when main thread
        # exits
        self.reader = Thread(target=self.reader_main)
        self.reader.start()

    def stop_fswatch(self):
        log.debug('Stopping fswatch')
        self.fswatch.terminate()

    def update_sessions(self, files):
        new_sessions = self.new_sessions(files)
        for mp in new_sessions:
            mp.start()
        for mp in new_sessions:
            mp.join()
            mp.save()

        self.sessions = new_sessions

    def get_next_files(self):
        # block for the first line
        lines = [self.files_queue.get()]
        while not self.files_queue.empty():
            lines.append(self.files_queue.get())

        return lines

    def new_sessions(self, files):
        return [
            MonitorSession(monitor_config, lf(monitor_config.includes_file, files))
            for monitor_config in self.config.monitors.values()
        ]

    def reader_main(self):
        for line in self.fswatch.stdout:
            line = self.config.normalize_path(line)
            log.debug('Got another path: %s', line)
            self.files_queue.put(line)

        log.debug('fswatch stdout closed, killing self')
        os.kill(os.getpid(), SIGTERM)

    def run(self):
        # Doesn't return
        self.start_fswatch()

        try:
            while True:
                next_files = self.get_next_files()
                assert len(next_files)
                log.info('Files changed:')
                for file in next_files:
                    log.info(f'  {file}')
                self.update_sessions(next_files)
        except BaseException as exc:
            log.debug('Exiting due to exception %s', exc)
            self.stop_fswatch()
            raise
