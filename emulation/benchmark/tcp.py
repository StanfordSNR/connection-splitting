import threading
from typing import Optional, Tuple

from benchmark import Benchmark
from network import EmulatedNetwork
from common import *


class LinuxTCPBenchmark(Benchmark):
    def __init__(self, net: EmulatedNetwork, label: str, logdir: str, n: str,
                 cca: str, certfile: str, keyfile: str, pep: bool=False):
        super().__init__(net, Protocol.LINUX_TCP, label, logdir, n, cca,
                         certfile, keyfile, pep)
        net.set_tcp_congestion_control(cca)

    def start_server(self, timeout: int=SETUP_TIMEOUT):
        cmd = f'python3 webserver/http_server.py --server-ip {self.server.IP()} '\
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
        logfile = self.logfile(self.server)
        self.net.popen(self.server, cmd, background=True,
            console_logger=DEBUG, logfile=logfile, func=notify_when_ready)
        with condition:
            notified = condition.wait(timeout=timeout)
            if not notified:
                raise TimeoutError(f'start_server timeout {timeout}s')

    def run_client(self, timeout: Optional[int]=None) -> Optional[Tuple[int, float]]:
        """Returns the status code and runtime (seconds) of the GET request.
        """
        cmd = f'python3 webserver/http_client.py --server-ip {self.server.IP()} '\
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

        logfile = self.logfile(self.client)
        timeout_flag = self.net.popen(self.client, cmd, background=False,
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
