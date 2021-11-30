import logging
import os
import re
import sys

import yaml

from .settings import CONFIG_FILE
from .utils import colour_text


log = logging.getLogger(__name__)


def normalize_key_value(key, value):
    if key.endswith('regex'):
        return key.replace('regex', 'pattern'), value and value.pattern

    return key, value


def dict_to_kwarg_str(dct):
    return ', '.join(
        f'{key}={value!r}' for key, value in (normalize_key_value(*kv) for kv in dct.items())
    )


class BadConfig(ValueError):
    pass


class ConfigObject:
    @staticmethod
    def normalize_path(path: str):
        path = os.path.normpath(path.strip())

        if os.path.isabs(path):
            cwd = os.getcwd()
            if os.path.commonpath([path, cwd]) != cwd:
                # this path is not in our directory
                return None

            return os.path.relpath(path)

        if path.split(os.sep)[0] == os.pardir:
            # this file is not in our directory
            return None

        return path

    def _check_and_init_pattern(self, attr, pattern):
        assert attr.endswith('pattern')

        if pattern is None:
            regex = None
        else:
            try:
                regex = re.compile(pattern, re.IGNORECASE)
            except re.error as exc:
                raise BadConfig(f'{attr} is not a valid regular expression: {exc}')

        setattr(self, attr.replace('pattern', 'regex'), regex)

    def __repr__(self):
        return f'{type(self).__name__}({dict_to_kwarg_str(self.__dict__)})'


class MonitorConfig(ConfigObject):
    # ----------------------------------------------------------------------------------------------
    # Instance API
    # ----------------------------------------------------------------------------------------------
    def __init__(
        self,
        name,
        command=None,
        file_pattern=None,
        problem_line_file_pattern=None,
        foreground_colour=None,
        background_colour=None,
    ):
        self.name = name

        if (
            not isinstance(command, list)
            or len(command) == 0
            or any(not isinstance(command_arg, str) for command_arg in command)
        ):
            raise BadConfig('command must be a non-empty list of the command and its arguments')

        self.command = command

        if not isinstance(file_pattern, (type(None), str)):
            raise BadConfig('file_pattern must be a valid regular expression')

        self._check_and_init_pattern('file_pattern', file_pattern)
        self._check_and_init_pattern('problem_line_file_pattern', problem_line_file_pattern)

        if foreground_colour is not None:
            try:
                colour_text('', foreground=foreground_colour)
            except KeyError:
                raise BadConfig('Unknown foreground color')
        self.foreground_colour = foreground_colour

        if background_colour is not None:
            try:
                colour_text('', background=background_colour)
            except KeyError:
                raise BadConfig('Unknown background color')
        self.background_colour = background_colour

    def includes_file(self, filepath):
        filedir, filename = os.path.split(filepath)
        return self.file_regex is None or bool(self.file_regex.search(filename))

    def extract_file_from_problem_line(self, line):
        if self.problem_line_file_regex is None:
            return None

        mo = self.problem_line_file_regex.search(line)
        if mo is None:
            return None

        try:
            return self.normalize_path(mo.group(1))
        except IndexError:
            return None

    def badge_for_number(self, number):
        if number == 0:
            return ''
        kwargs = {}
        if self.foreground_colour is not None:
            kwargs['foreground'] = self.foreground_colour
        if self.background_colour is not None:
            kwargs['background'] = self.background_colour
        return colour_text(f' {number} ', **kwargs)

        # ----------------------------------------------------------------------------------------------
        # Magic methods
        # ----------------------------------------------------------------------------------------------
        return self.name


class GlobalConfig(ConfigObject):
    def __init__(self, monitors=None):
        if monitors is None:
            raise BadConfig('No monitors specified')

        if not isinstance(monitors, dict):
            raise BadConfig(
                'monitors section must be a dictionary of named monitors (each itself a dictionary)'
            )

        if len(monitors) == 0:
            raise BadConfig('Empty monitors dictionary')

        self.monitors = {}
        self.monitor_errors = []
        for name, mon_con in monitors.items():

            try:
                self.monitors[name] = clean_monitor_config(name, mon_con)
            except BadConfig as exc:
                self.monitor_errors.append(f'Monitor "{name}" invalid: {exc}')

        if len(self.monitors) == 0:
            raise BadConfig(f'No valid monitors: {"; ".join(self.monitor_errors)}')

        log.debug('cleaned config: %r', self)


def clean_monitor_config(name, monitor_config):
    if not isinstance(monitor_config, dict):
        raise BadConfig('Not a dictionary')

    return MonitorConfig(name, **monitor_config)


def clean_config(config):
    if not isinstance(config, dict):
        raise BadConfig('Config is not a dictionary')

    return GlobalConfig(**config)


def load_config_file(config_file):
    log.debug('Load config')
    if not os.path.exists(config_file):
        raise BadConfig('No such config file')

    with open(config_file, "r") as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            oneline_exc = str(exc).replace('\n', ' ')
            raise BadConfig(f'Invaid YAML file: {oneline_exc}') from exc

    return clean_config(config)


def load_config_or_exit():
    try:
        return load_config_file(CONFIG_FILE)
    except BadConfig as exc:
        log.error('Bad config file %s: %s', CONFIG_FILE, exc)
        sys.exit(1)
