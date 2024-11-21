import os
import json
import select
import statistics
import subprocess
import time

from collections import defaultdict
from typing import List, Tuple

from common import SIDEKICK_HOME
from experiment import Treatment, NetworkSetting, Experiment

DATA_HOME = f'{SIDEKICK_HOME}/data'


class RawDataFile:
    def __init__(self, treatment: Treatment, network_setting: NetworkSetting):
        self._treatment = treatment
        self._network_setting = network_setting
        base_dir = f'{DATA_HOME}/{network_setting.label()}'
        self.base_path = f'{base_dir}/{treatment.label()}'
        os.system(f'mkdir -p {base_dir}')
        os.system(f'touch {self.stdout_filename()}')
        os.system(f'touch {self.stderr_filename()}')
        os.system(f'touch {self.fulllog_filename()}')

    def treatment(self) -> str:
        return self._treatment.label()

    def network_setting(self) -> str:
        return self._network_setting.label()

    def stdout_filename(self) -> str:
        return f'{self.base_path}.stdout'

    def stderr_filename(self) -> str:
        return f'{self.base_path}.stderr'

    def fulllog_filename(self) -> str:
        return f'{self.base_path}.log'

    def cmd(self, data_size: int, num_trials: int):
        cmd = ['sudo -E python3 emulation/main.py']
        for key in self._network_setting.labels:
            cmd.append(f'--{key}')
            cmd.append(str(self._network_setting.settings[key]))
        cmd.append('-t')
        cmd.append(str(num_trials))
        cmd.append('--label')
        cmd.append(self._treatment.label())
        protocol = self._treatment.protocol
        cmd.append(protocol)
        if protocol == 'tcp':
            if self._treatment.pep:
                cmd.append('--pep')
            if self._treatment.cca:
                cmd.append('-cca')
                cmd.append(self._treatment.cca)
            cmd.append('-n')
            cmd.append(str(data_size))
        return ' '.join(cmd)


class RawDataParser:
    def __init__(self, exp: Experiment):
        self.exp = exp
        self.data = {}
        self._data_sizes = set(exp.data_sizes)
        self._reset()
        self._parse_files()

    def _reset(self):
        self.data = {}  # treatment -> network_setting -> data_size -> [value]
        for treatment in self.exp.treatments:
            self.data[treatment] = {}
            for network_setting in self.exp.network_settings:
                self.data[treatment][network_setting] = defaultdict(lambda: [])

    def _parse_files(self):
        for treatment in self.exp.get_treatments():
            for network_setting in self.exp.get_network_settings():
                file = RawDataFile(treatment, network_setting)
                self._parse_file(file)

    def _parse_file(self, file: RawDataFile):
        filename = file.stdout_filename()
        with open(filename) as f:
            for line in f:
                line = line.strip()
                try:
                    line = json.loads(line)
                except Exception as e:
                    print('parsing error:', e)
                    continue
                for data_size, output in self._parse_line(line):
                    self._maybe_add(
                        file.treatment(),
                        file.network_setting(),
                        data_size,
                        output,
                    )

    def _parse_line(self, line):
        """
        Input: Parsed JSON line from experiment logs
        Output: The parsed data size and outputs
        """
        data_size = line['inputs']['data_size']
        for output in line['outputs']:
            if output['success']:
                yield (data_size, output)

    def _maybe_add(self, treatment: str, network_setting: str, data_size: int,
                  value) -> bool:
        # Don't add the value if it is not one of the requested data points
        if treatment not in self.data:
            return False
        if network_setting not in self.data[treatment]:
            return False
        if data_size not in self._data_sizes:
            return False

        # Add the value if number of trials not exceeded
        values = self.data[treatment][network_setting][data_size]
        if len(values) >= self.exp.num_trials:
            return False
        values.append(value)
        return True


class RawData(RawDataParser):
    def __init__(self, exp: Experiment, execute=False, max_retries=5):
        super().__init__(exp)

        for i in range(max_retries):
            missing_data = self._find_missing_data()
            if len(missing_data) == 0 or not execute:
                break
            self._collect_missing_data(missing_data)
            self._reset()
            self._parse_files()

        # Print remaining missing data
        for file, data_size, num_missing in missing_data:
            print('MISSING:', file.cmd(data_size, num_missing))

    def _find_missing_data(self) -> List[Tuple[RawDataFile, int, int]]:
        missing_data = []
        for treatment in self.exp.get_treatments():
            for network_setting in self.exp.get_network_settings():
                file = RawDataFile(treatment, network_setting)
                subdata = self.data[treatment.label()][network_setting.label()]
                for data_size in self.exp.data_sizes:
                    num_results = len(subdata[data_size])
                    num_missing = self.exp.num_trials - num_results
                    if num_missing == 0:
                        continue
                    missing_data.append((file, data_size, num_missing))
        return missing_data

    def _collect_missing_data(
        self,
        missing_data: List[Tuple[RawDataFile, int, int]],
        chunk_size: int=10,
    ):
        print(len(missing_data))
        for file, data_size, num_missing in missing_data:
            remaining = num_missing
            while remaining != 0:
                num_trials = min(chunk_size, remaining)
                start = time.time()
                self._execute_chunk(file, data_size, num_trials)
                print(time.time() - start)
                remaining -= num_trials

    def _execute_chunk(self, file: RawDataFile, data_size: int, num_trials: int):
        # Start the process
        cmd = file.cmd(data_size, num_trials)
        print(cmd, end=' ')
        p = subprocess.Popen(
            cmd.split(' '),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=SIDEKICK_HOME,
            text=True,
        )

        # Write process output to the appropriate logfiles
        with open(file.stdout_filename(), 'a') as stdout,\
             open(file.stderr_filename(), 'a') as stderr,\
             open(file.fulllog_filename(), 'a') as fulllog:
            while p.poll() is None:
                ready, _, _ = select.select([p.stdout, p.stderr], [], [])
                for stream in ready:
                    line = stream.readline()
                    if not line:
                        continue
                    if stream == p.stdout:
                        stdout.write(line)
                    if stream == p.stderr:
                        stderr.write(line)
                    fulllog.write(line)

        # Cleanup the process
        exitcode = p.wait()
        if exitcode != 0:
            print(f'execute error: {exitcode}')
            exit(1)


class PlottableDataPoint:
    def __init__(self, raw_data):
        self.raw_data = raw_data
        self.sorted_data = list(sorted(raw_data))
        self.n = len(raw_data)
        if self.n == 0:
            self.mean = None
            self.std = None
        elif self.n == 1:
            self.mean = statistics.mean(raw_data)
            self.std = None
        else:
            self.mean = statistics.mean(raw_data)
            self.std = statistics.stdev(raw_data)

    def p(self, pct):
        assert 0 <= pct < 100
        if self.n == 0:
            return None
        i = int(self.n * pct / 100.0)
        return self.sorted_data[i]


class PlottableData:
    def __init__(self, data: RawData, metric: str):
        self.data = defaultdict(lambda: defaultdict(lambda: {}))
        self.treatments = data.exp.treatments
        self.network_settings = data.exp.network_settings
        self.data_sizes = data.exp.data_sizes
        self.metric = metric
        for treatment in self.treatments:
            for network_setting in self.network_settings:
                results = data.data[treatment][network_setting]
                for data_size, outputs in results.items():
                    if len(outputs) == 0:
                        continue
                    values = [output[metric] for output in outputs]
                    pdp = PlottableDataPoint(values)
                    self.data[treatment][network_setting][data_size] = pdp
