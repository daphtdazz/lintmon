import logging
import os
import re
from contextlib import contextmanager

import psutil

from .config import load_config_file, BadConfig, load_config_or_exit
from .dirmon import Dirmon
from .settings import CONFIG_FILE, DEFAULT_IGNORED_DIRECTORY_NAMES, PID_FILE, STATE_DIR


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


def dirmond():
    log.debug('dirmond main')

    dirmon = Dirmon(load_config_or_exit())
    dirmon.run()


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
    dirmon = Dirmon(config)
    dirmon.update_sessions(files)

    for ms in dirmon.sessions:
        if len(ms.problem_lines) == 0:
            print(f'✅ Monitor {ms} clean')
            continue

        coloured = ms.badge
        print(f'{coloured} Monitor {ms} output:')
        for ol in (pl for pls in ms.problem_lines.values() for pl in pls):
            print(f'  {ol}')


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

    dirmon = Dirmon(config)
    dirmon.load_latest_sessions()

    print(dirmon.badges, end='')


# ensure_dirmon_is_running()
