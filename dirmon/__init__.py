import atexit
import io
import logging
import os
import re
from contextlib import contextmanager
from queue import SimpleQueue
from subprocess import Popen, PIPE
from threading import Thread

import psutil

from .config import load_config_file, BadConfig, load_config_or_exit
from .monitor_session import MonitorSession
from .settings import CONFIG_FILE, DEFAULT_IGNORED_DIRECTORY_NAMES, PID_FILE, STATE_DIR
from .utils import lf


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING)


@contextmanager
def timer(name):
    import time

    start = time.time()

    try:
        yield
    finally:
        log.debug('%s took %.3f seonds', name, time.time() - start)


class Dirmond:

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
            line = line.strip()
            log.debug('Got another line: %s', line)
            self.files_queue.put(line)

    def run(self):
        self.start_fswatch()

        while True:
            next_files = self.get_next_files()
            log.debug('Got next files %s', next_files)
            assert len(next_files)
            self.update_sessions(next_files)


def dirmond():
    log.debug('dirmond main')

    dirmond = Dirmond(load_config_or_exit())
    dirmond.run()


def find_all_appropriate_files():
    full_file_paths = []
    for dirpath, subdirs, files in os.walk(os.curdir):
        for file in files:
            full_file_paths.append(os.path.join(dirpath, file))

        for ignored_subdir in DEFAULT_IGNORED_DIRECTORY_NAMES:
            try:
                subdirs.remove(ignored_subdir)
            except ValueError:
                pass

    return full_file_paths


def run_all():
    log.debug('Run all')
    config = load_config_or_exit()
    files = find_all_appropriate_files()
    dirmond = Dirmond(config)
    dirmond.update_sessions(files)

    for ms in dirmond.sessions:
        if len(ms.problem_lines) == 0:
            print(f'✅ Monitor {ms.config.name} clean')
            continue

        coloured = ms.badge
        print(f'{coloured} Monitor {ms.config.name} output:')
        for ol in (pl for pls in ms.problem_lines.values() for pl in pls):
            print(f'  {ol}')

        if any(pf is not None for pf in ms.problem_lines):
            print(
                f'{len([pf for pf in ms.problem_lines if pf is not None])} bad files:'
            )
            for pf in ms.problem_lines:
                if pf is None:
                    continue
                print(f'  {pf}')

        # temp
        ms.save()


def directory_is_sane():
    if not os.path.isdir(STATE_DIR):
        if os.path.exists(STATE_DIR):
            return False

        os.mkdir(STATE_DIR)
    return True


def dirmon_is_running():
    if not os.path.exists(PID_FILE):
        return False

    with open(PID_FILE) as pf:
        pid_line = pf.readline()

    mo = re.match(r'(\d+)', pid_line)
    if not mo:
        return False

    pid = int(mo.group(1))
    return psutil.pid_exists(pid)


def ensure_dirmon_is_running():
    if dirmon_is_running():
        log.debug('dirmon running')
        return

    log.debug('dirmon not running')


def red(text):
    # echo -n $'\x1b[41m'' ! '$'\x1b[0m'

    return '\x1b[41m' + text + '\x1b[0m'


def status_prompt():
    log.debug('status_prompt')

    ensure_dirmon_is_running()

    try:
        config = load_config_file(CONFIG_FILE)
    except BadConfig as exc:
        if 'No such config file' in str(exc):
            return 0
        print(red(' ! '), end='')
        return 1

    config = load_config_or_exit()

    dirmond = Dirmond(config)
    dirmond.load_latest_sessions()

    print(dirmond.badges, end='')


# ensure_dirmon_is_running()
