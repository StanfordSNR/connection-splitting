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


class BenchmarkResult:
    def __init__(self, protocol: Protocol, data_size: int, cca: str, pep: bool):
        self.inputs = {
            'protocol': protocol.name,
            'start_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'data_size': data_size,
            'cca': cca,
            'pep': pep,
            'num_trials': 1,
        }
        self.outputs = {
            'success': False,
        }

    def set_success(self, success: bool):
        self.outputs['success'] = success

    def set_time_s(self, time_s: float):
        self.outputs['time_s'] = time_s
        self.outputs['throughput_mbps'] = \
            8 * self.inputs['data_size'] / 1000000 / time_s

    def set_network_statistics(self, statistics):
        self.outputs['statistics'] = statistics

    def print(self):
        result = {
            'inputs': self.inputs,
            'outputs': [self.outputs],
        }
        print(json.dumps(result, indent=2))


class BaseBenchmark:
    def __init__(self, net):
        self.net = net

    def start_sidekick(self):
        pass


class QUICBenchmark(BaseBenchmark):
    def __init__(self, net, n: str, certfile=None, keyfile=None):
        super().__init__(net)
        self.certfile = certfile
        self.keyfile = keyfile

        # Create cache dir
        self.cache_dir = '/tmp/quic-data/www.example.org'
        filename = f'{self.cache_dir}/index.html'
        net.popen(None, f'mkdir -p {self.cache_dir}', console_logger=DEBUG)
        # net.popen(None, f'head -c {n} /dev/urandom > {filename}', console_logger=DEBUG)

    def start_server(self, logfile):
        base = 'deps/chromium/src'
        cmd = f'./{base}/out/Default/quic_server '\
        f'--quic_response_cache_dir=/tmp/quic-data/www.example.org '\
        f'--certificate_file={self.certfile} '\
        f'--key_file={self.keyfile}'
        self.net.popen(self.net.h2, cmd, background=True,
            console_logger=DEBUG, logfile=logfile)

    def run_client(self, logfile):
        base = 'deps/chromium/src'
        cmd = f'./{base}/out/Default/quic_client --allow_unknown_root_cert '\
        f'--host={self.net.h2.IP()} --port=6121 https://www.example.org/'
        self.net.popen(self.net.h1, cmd, background=False,
            console_logger=DEBUG, logfile=logfile)

    def run(self, logdir):
        self.start_server(logfile=f'{logdir}/{SERVER_LOGFILE}')
        start = time.monotonic()
        self.run_client(logfile=f'{logdir}/{CLIENT_LOGFILE}')
        end = time.monotonic()
        print(f'{end - start:.3f}')


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
        cmd = f'python webserver/http_server.py --server-ip {self.server_ip} '\
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
        with condition:
            self.net.popen(self.net.h2, cmd, background=True,
                console_logger=DEBUG, logfile=logfile, func=notify_when_ready)
            condition.wait()

    def run_client(self, logfile) -> Optional[Tuple[int, float]]:
        """Returns the status code and runtime (seconds) of the GET request.
        """
        cmd = f'python webserver/http_client.py --server-ip {self.server_ip} '\
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

        self.net.popen(self.net.h1, cmd, background=False,
            console_logger=DEBUG, logfile=logfile, func=parse_result)
        if len(result) == 0:
            WARN('TCP client failed to return result')
        elif len(result) > 1:
            WARN(f'TCP client returned multiple results {result}')
        else:
            return result[0]

    def start_tcp_pep(self, logfile):
        self.net.popen(self.net.r1, 'ip rule add fwmark 1 lookup 100')
        self.net.popen(self.net.r1, 'ip route add local 0.0.0.0/0 dev lo table 100')
        self.net.popen(self.net.r1, 'iptables -t mangle -F')
        self.net.popen(self.net.r1, 'iptables -t mangle -A PREROUTING -i r1-eth1 -p tcp -j TPROXY --on-port 5000 --tproxy-mark 1')
        self.net.popen(self.net.r1, 'iptables -t mangle -A PREROUTING -i r1-eth0 -p tcp -j TPROXY --on-port 5000 --tproxy-mark 1')

        condition = threading.Condition()
        def notify_when_ready(line):
            if 'Pepsal started' in line:
                with condition:
                    condition.notify()

        # The start_tcp_pep() function blocks until the TCP PEP is ready to
        # split connections. That is, when we observe the 'Pepsal started'
        # string in the router output.
        with condition:
            self.net.popen(self.net.r1, 'pepsal -v', background=True,
                console_logger=DEBUG, logfile=logfile, func=notify_when_ready)
            condition.wait()

    def run(self, logdir):
        # Start the server
        self.start_server(logfile=f'{logdir}/{SERVER_LOGFILE}')

        # Start the TCP PEP
        if self.pep:
            self.start_tcp_pep(logfile=f'{logdir}/{ROUTER_LOGFILE}')

        # Run the client
        result = BenchmarkResult(
            protocol=Protocol.TCP,
            data_size=self.n,
            cca=self.cca,
            pep=self.pep,
        )
        self.net.reset_statistics()
        output = self.run_client(logfile=f'{logdir}/{CLIENT_LOGFILE}')
        statistics = self.net.snapshot_statistics()
        result.set_network_statistics(statistics)
        if output is not None:
            status_code, time_s = output
            result.set_success(status_code == 200)
            result.set_time_s(time_s)
        result.print()


class WebRTCBenchmark(BaseBenchmark):
    def __init__(self, net):
        super().__init__(net)

    def start_webrtc_sender(self):
        pass

    def start_webrtc_receiver(self):
        pass
