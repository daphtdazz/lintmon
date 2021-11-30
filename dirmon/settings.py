import os

CONFIG_FILE = 'dirmon.yaml'
DEFAULT_IGNORED_DIRECTORY_NAMES = [r'\.dirmon', r'\.git', 'node_modules', '__pycache__']
STATE_DIR = '.dirmon'
PID_FILE = os.path.join(STATE_DIR, 'pid')
STOP_WAIT_SECONDS = 10
STOP_FILE = os.path.join(STATE_DIR, 'stop')
