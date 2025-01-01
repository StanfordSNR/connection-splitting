import json
import time
import threading
from datetime import datetime
from enum import Enum
from typing import Optional, Tuple

from common import *


class Protocol(Enum):
    QUIC = 0
    TCP = 1
    TCP_IPERF3 = 2


class BenchmarkResult:
    def __init__(self, label: str, protocol: Protocol,
                 data_size: int, cca: str, pep: bool):
        self.inputs = {
            'label': label,
            'protocol': protocol.name,
            'num_trials': 0,
            'start_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'data_size': data_size,
            'cca': cca,
            'pep': pep,
        }
        self.outputs = []

    def append_new_output(self):
        self.inputs['num_trials'] += 1
        self.outputs.append({
            'success': False,
        })

    def set_success(self, success: bool):
        self.outputs[-1]['success'] = success

    def set_timeout(self, timeout: bool):
        self.outputs[-1]['timeout'] = timeout

    def set_time_s(self, time_s: float):
        self.outputs[-1]['time_s'] = time_s
        self.outputs[-1]['throughput_mbps'] = \
            8 * self.inputs['data_size'] / 1000000 / time_s

    def set_network_statistics(self, statistics):
        self.outputs[-1]['statistics'] = statistics

    def set_additional_data(self, data):
        self.outputs[-1]['additional_data'] = data

    def print(self, pretty_print=False):
        result = {
            'inputs': self.inputs,
            'outputs': self.outputs,
        }
        if pretty_print:
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps(result))


class BaseBenchmark:
    def __init__(self, net):
        self.net = net

    def start_sidekick(self):
        pass


class QUICBenchmark(BaseBenchmark):
    def __init__(self, net, n: str, cca: str, certfile=None, keyfile=None):
        super().__init__(net)
        self.n = n
        self.cca = cca
        self.certfile = certfile
        self.keyfile = keyfile
        self.server_ip = self.net.h2.IP()

        # Create cache dir
        # self.cache_dir = '/tmp/quic-data/www.example.org'
        # filename = f'{self.cache_dir}/index.html'
        # net.popen(None, f'mkdir -p {self.cache_dir}', console_logger=DEBUG)
        # net.popen(None, f'head -c {n} /dev/urandom > {filename}', console_logger=DEBUG)

    def start_server(self, logfile):
        base = 'deps/chromium/src'
        cmd = f'./{base}/out/Default/quic_server '\
              f'--certificate_file={self.certfile} '\
              f'--key_file={self.keyfile} '\
              f'--num_cached_bytes={self.n}'

        condition = threading.Condition()
        def notify_when_ready(line):
            if 'Serving' in line:
                with condition:
                    condition.notify()

        # The start_server() function blocks until the server is ready to
        # accept client requests. That is, when we observe the 'Serving'
        # string in the server output.
        self.net.popen(self.net.h2, cmd, background=True,
            console_logger=DEBUG, logfile=logfile, func=notify_when_ready)
        with condition:
            notified = condition.wait(timeout=SETUP_TIMEOUT)
            if not notified:
                raise TimeoutError(f'start_server timeout {SETUP_TIMEOUT}s')

    def run_client(self, logfile, timeout) -> Optional[Tuple[int, float]]:
        """Returns the status code and runtime (seconds) of the GET request.
        """
        base = 'deps/chromium/src'
        cmd = f'./{base}/out/Default/quic_client '\
              f'--allow_unknown_root_cert '\
              f'--host={self.net.h2.IP()} --port=6121 '\
              f'https://www.example.org/{self.n} '

        # Add the congestion control algorithm options
        cca_to_option = {
            'cubic': 'BYTE',
            'reno': 'RENO',
            'bbr1': 'TBBR',
            'bbr': 'B2ON',
        }
        if self.cca in cca_to_option:
            option = cca_to_option[self.cca]
            cmd += f'--client_connection_options={option} '
            cmd += f'--connection_options={option} '

        result = []
        def parse_result(line):
            if not line.startswith('[QUIC_CLIENT]'):
                return
            try:
                line = line.split(' ')[1:]
                line = [kv.split('=') for kv in line]
                assert line[0][0] == 'status_code'
                assert line[1][0] == 'time_s'
                status_code = int(line[0][1])
                time_s = float(line[1][1].strip()[:-1])  # output ends in "s"
                result.append((status_code, time_s))
            except:
                pass

        timeout_flag = self.net.popen(self.net.h1, cmd, background=False,
            console_logger=DEBUG, logfile=logfile, func=parse_result,
            timeout=timeout)
        if timeout_flag:
            return (HTTP_TIMEOUT_STATUSCODE, timeout)
        elif len(result) == 0:
            WARN('QUIC client failed to return result')
        elif len(result) > 1:
            WARN(f'QUIC client returned multiple results {result}')
        else:
            return result[0]

    def run(self, label, logdir, num_trials, timeout, network_statistics):
        # Start the server
        self.start_server(logfile=f'{logdir}/{SERVER_LOGFILE}')

        # Initialize remaining trials
        num_trials_left = num_trials

        # Run the client
        while num_trials_left > 0:
            result = BenchmarkResult(
                label=label,
                protocol=Protocol.QUIC,
                data_size=self.n,
                cca=self.cca,
                pep=False,
            )

            # Log output every LOG_CHUNK_TIME while continuing to run trials
            total_time_s = 0
            while num_trials_left > 0 and total_time_s < LOG_CHUNK_TIME:
                result.append_new_output()
                self.net.reset_statistics()
                output = self.run_client(
                    logfile=f'{logdir}/{CLIENT_LOGFILE}',
                    timeout=timeout,
                )

                # Error
                if output is None:
                    ERROR('no output')
                    num_trials_left -= 1
                    continue

                # Success
                if network_statistics:
                    statistics = self.net.snapshot_statistics()
                    result.set_network_statistics(statistics)
                status_code, time_s = output
                result.set_success(status_code == HTTP_OK_STATUSCODE)
                result.set_timeout(status_code == HTTP_TIMEOUT_STATUSCODE)
                result.set_time_s(time_s)

                total_time_s += time_s
                num_trials_left -= 1
            result.print()


class TCPBenchmark(BaseBenchmark):
    def __init__(
        self,
        net,
        n: int,
        cca: str,
        pep: bool,
        certfile=None,
        keyfile=None,
    ):
        super().__init__(net)
        net.set_tcp_congestion_control(cca)

        self.n = n
        self.cca = cca
        self.pep = pep
        self.certfile = certfile
        self.keyfile = keyfile
        self.server_ip = self.net.h2.IP()

    def start_server(self, logfile):
        cmd = f'python3 webserver/http_server.py --server-ip {self.server_ip} '\
              f'--certfile {self.certfile} --keyfile {self.keyfile} '\
              f'-n {self.n}'

        condition = threading.Condition()
        def notify_when_ready(line):
            if 'Serving' in line:
                with condition:
                    condition.notify()

        # The start_server() function blocks until the server is ready to
        # accept client requests. That is, when we observe the 'Serving'
        # string in the server output.
        self.net.popen(self.net.h2, cmd, background=True,
            console_logger=DEBUG, logfile=logfile, func=notify_when_ready)
        with condition:
            notified = condition.wait(timeout=SETUP_TIMEOUT)
            if not notified:
                raise TimeoutError(f'start_server timeout {SETUP_TIMEOUT}s')

    def run_client(self, logfile, timeout) -> Optional[Tuple[int, float]]:
        """Returns the status code and runtime (seconds) of the GET request.
        """
        cmd = f'python3 webserver/http_client.py --server-ip {self.server_ip} '\
              f'-n {self.n}'

        result = []
        def parse_result(line):
            if not line.startswith('[TCP_CLIENT]'):
                return
            try:
                line = line.split(' ')[1:]
                line = [kv.split('=') for kv in line]
                assert line[0][0] == 'status_code'
                assert line[1][0] == 'time_s'
                status_code = int(line[0][1])
                time_s = float(line[1][1])
                result.append((status_code, time_s))
            except:
                pass

        timeout_flag = self.net.popen(self.net.h1, cmd, background=False,
            console_logger=DEBUG, logfile=logfile, func=parse_result,
            timeout=timeout)
        if timeout_flag:
            return (HTTP_TIMEOUT_STATUSCODE, timeout)
        elif len(result) == 0:
            WARN('TCP client failed to return result')
        elif len(result) > 1:
            WARN(f'TCP client returned multiple results {result}')
        else:
            return result[0]

    def run(self, label, logdir, num_trials, timeout, network_statistics):
        # Start the server
        self.start_server(logfile=f'{logdir}/{SERVER_LOGFILE}')

        # Start the TCP PEP
        if self.pep:
            self.net.start_tcp_pep(logfile=f'{logdir}/{ROUTER_LOGFILE}')

        # Initialize remaining trials
        num_trials_left = num_trials

        # Run the client
        while num_trials_left > 0:
            result = BenchmarkResult(
                label=label,
                protocol=Protocol.TCP,
                data_size=self.n,
                cca=self.cca,
                pep=self.pep,
            )

            # Log output every LOG_CHUNK_TIME while continuing to run trials
            total_time_s = 0
            while num_trials_left > 0 and total_time_s < LOG_CHUNK_TIME:
                result.append_new_output()
                self.net.reset_statistics()
                output = self.run_client(
                    logfile=f'{logdir}/{CLIENT_LOGFILE}',
                    timeout=timeout,
                )

                # Error
                if output is None:
                    ERROR('no output')
                    num_trials_left -= 1
                    continue

                # Success
                if network_statistics:
                    statistics = self.net.snapshot_statistics()
                    result.set_network_statistics(statistics)
                status_code, time_s = output
                result.set_success(status_code == HTTP_OK_STATUSCODE)
                result.set_timeout(status_code == HTTP_TIMEOUT_STATUSCODE)
                result.set_time_s(time_s)

                total_time_s += time_s
                num_trials_left -= 1
            result.print()


class WebRTCBenchmark(BaseBenchmark):
    def __init__(self, net):
        super().__init__(net)

    def start_webrtc_sender(self):
        pass

    def start_webrtc_receiver(self):
        pass

class Iperf3Benchmark(BaseBenchmark):
    def __init__(
        self,
        net,
        n: int,
        cca: str,
        pep: bool,
    ):
        super().__init__(net)
        self.n = n
        self.pep = pep
        self.cca = cca

    def start_server(self, logfile):
        cmd = 'iperf3 -s'
        condition = threading.Condition()

        def notify_when_ready(line):
            if 'Server listening' in line:
                with condition:
                    condition.notify()

        self.net.popen(self.net.h2, cmd, background=True,
                       console_logger=DEBUG, logfile=logfile,
                       func=notify_when_ready)
        with condition:
            notified = condition.wait(timeout=SETUP_TIMEOUT)
            if not notified:
                raise TimeoutError(f'start_server timeout {SETUP_TIMEOUT}s')

    def run_client(self, logfile, outfile, timeout):
        cmd = f'iperf3 -c {self.net.h2.IP()} '
        cmd += f'-n {self.n} '
        cmd += f'--json > {outfile}'

        timeout_flag = self.net.popen(self.net.h1, cmd, background=False,
            console_logger=DEBUG, logfile=logfile,
            timeout=timeout)

        if timeout_flag:
            return False
        return True

    def run(self, label, logdir, num_trials, timeout, network_statistics,
            additional_data):
        self.start_server(logfile=f'{logdir}/{SERVER_LOGFILE}')
        if self.pep:
            self.net.start_tcp_pep(logfile=f'{logdir}/{ROUTER_LOGFILE}')
        num_trials_left = num_trials

        while num_trials_left > 0:

            result = BenchmarkResult(
                label=label,
                protocol=Protocol.TCP_IPERF3,
                data_size=self.n,
                cca=self.cca,
                pep=self.pep,
            )

            total_time_s = 0
            while num_trials_left > 0 and total_time_s < LOG_CHUNK_TIME:
                result.append_new_output()
                self.net.reset_statistics()
                success = self.run_client(
                            logfile=f'{logdir}/{CLIENT_LOGFILE}',
                            outfile = 'tmp.json',
                            timeout=timeout,
                        )

                if not success:
                    ERROR("Failed iperf3 test")
                    num_trials_left -= 1
                    continue

                if network_statistics:
                    statistics = self.net.snapshot_statistics()
                    result.set_network_statistics(statistics)

                result.set_success(True)
                json_data = json.load(open('tmp.json', 'r'))
                os.system('sudo rm tmp.json')
                if additional_data:
                    result.set_additional_data(json_data)
                result.set_time_s(json_data['end']['sum_received']['seconds'])
                total_time_s += total_time_s
                num_trials_left -= 1

            result.print()

