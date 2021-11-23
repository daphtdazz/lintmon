import logging
import os
from subprocess import Popen
from tempfile import TemporaryFile

from .settings import STATE_DIR
from .utils import gb


log = logging.getLogger(__name__)


class MonitorSession:
    class States:
        initial = 'initial'
        running = 'running'
        complete = 'complete'

    @property
    def badge(self):
        num_problems = sum(len(lines) for lines in self.problem_lines.values())
        return self.config.badge_for_number(num_problems)

    @property
    def dirpath(self):
        return os.path.join(STATE_DIR, 'monitors', self.config.name)

    @property
    def problem_lines_filepath(self):
        return os.path.join(self.dirpath, 'problem_lines')

    @property
    def problem_files_filepath(self):
        return os.path.join(self.dirpath, 'problem_files')

    def __init__(self, config, files):
        self.state = self.States.initial
        self.config = config
        self.files = files
        self.process = None
        self.output_file = None
        self.problem_lines = None

        self.initial_problem_lines = gb(
            self._read_lines_filepath(self.problem_lines_filepath),
            self.config.extract_file_from_problem_line,
        )

    def start(self):
        assert self.state == self.States.initial

        if len(self.files) == 0:
            self.skip()
            return

        self.state = self.States.running
        log.debug('Starting %s on %d files', self.config.command, len(self.files))
        self.output_file = TemporaryFile(mode='w+')
        try:
            self.process = Popen(
                [*self.config.command, *self.files],
                stdout=self.output_file,
                stderr=self.output_file,
            )
        except Exception as exc:
            self.problem_lines = [str(exc).replace('\n', ' ')]
            # self.problem_files = []
            self.process = None

    def join(self):
        if self.state == self.States.complete:
            return

        assert self.state == self.States.running
        if self.process is None:
            self.state = self.States.complete
            return

        self.process.communicate()
        self.output_file.flush()
        self.output_file.seek(0)
        self.problem_lines = gb(
            (l.strip() for l in self.output_file.readlines()),
            self.config.extract_file_from_problem_line,
        )
        self.output_file.close()
        self.output_file = None
        self.process = None
        self.state = self.States.complete

    def skip(self):
        # don't bother running, just use initial values as end values
        assert self.state == self.States.initial
        self.problem_lines = self.initial_problem_lines
        self.state = self.States.complete

    def save(self):
        # only able to save once it has been joined
        assert self.state == self.States.complete
        assert self.problem_lines is not None

        new_problem_lines_by_file = {
            **self.initial_problem_lines,
            **self.problem_lines,
        }

        if new_problem_lines_by_file == self.initial_problem_lines:
            log.debug('No change, no need to save %s', self)
            return

        expanded_sorted_lines = [
            line
            for file, lines in sorted(
                new_problem_lines_by_file.items(), key=lambda k_v: k_v[0] or ''
            )
            for line in lines
        ]

        self._write_lines_filepath(self.problem_lines_filepath, expanded_sorted_lines)
        self._write_lines_filepath(
            self.problem_files_filepath,
            sorted([k for k in new_problem_lines_by_file.keys() if k is not None]),
        )

    def _read_lines_filepath(self, filepath):
        if not os.path.exists(filepath):
            return []

        with open(filepath) as file:
            return [line.strip() for line in file.readlines()]

    def _write_lines_filepath(self, filepath, problem_lines):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as file:
            for line in problem_lines:
                print(line, file=file)
