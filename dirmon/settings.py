import os

CONFIG_FILE = 'dirmon.yaml'
DEFAULT_IGNORED_DIRECTORY_NAMES = ['.git', 'node_modules']
STATE_DIR = '.dirmon'
PID_FILE = os.path.join(STATE_DIR, 'pid')
