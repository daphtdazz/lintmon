import atexit
import logging
import os
from queue import SimpleQueue
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
        log.debug('Running: %s', ' '.join(args))
        self.files_queue = SimpleQueue()
        self.fswatch = Popen(
            args,
            stdout=PIPE,
            stderr=PIPE,
            encoding='utf8',
        )
        atexit.register(self.fswatch.terminate)

        self.reader = Thread(target=self.reader_main)
        self.reader.start()

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

    def run(self):
        self.start_fswatch()

        while True:
            next_files = self.get_next_files()
            log.debug('Got next files %s', next_files)
            assert len(next_files)
            self.update_sessions(next_files)
            print(self.badges)
