import re
import time
from typing import Optional, Tuple

from benchmark import Benchmark
from network import EmulatedNetwork
from common import *


class PicoQUICBenchmark(Benchmark):
    def __init__(
        self, net: EmulatedNetwork, label: str, logdir: str, n: str,
        cca: str, certfile: str, keyfile: str, pep: bool=False,
    ):
        super().__init__(net, Protocol.PICOQUIC, label, logdir, n, cca,
                         certfile, keyfile, pep)

    def start_server(self, timeout: int=SETUP_TIMEOUT):
        base = 'deps/picoquic'
        cmd = f'./{base}/picoquic_sample '\
              f'server '\
              f'4433 '\
              f'{self.certfile} '\
              f'{self.keyfile} '\
              f'. '\
              f'{self.n} '\
              f'{self.cca}'

        DEBUG(f'{self.server.name} {cmd}')
        self.server.cmd(cmd + ' &')
        time.sleep(2)

        '''
        TODO FIGURE OUT WHY POPEN ISN'T STARTING for picoquic
        condition = threading.Condition()
        def notify_when_ready(line):
            if 'serving' in line.lower():
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
                WARN("Server did not print expected output; continuing anyway")
                # raise TimeoutError(f'start_server timeout {timeout}s')
        '''

    def run_client(self, timeout: Optional[int]=None) -> Optional[Tuple[int, float]]:
        """Returns the status code and runtime (seconds) of the GET request.
        """
        base = 'deps/picoquic'
        cmd = f'./{base}/picoquic_sample '\
              f'client '\
              f'{self.server.IP()} '\
              f'4433 '\
              f'/tmp '\
              f'{self.cca} '\
              f'{self.n}.html '
        if timeout is None:
            DEBUG(f'{self.client.name} {cmd}')
            output = self.client.cmd(cmd)
        else:
            DEBUG(f'{self.client.name} timeout {timeout} {cmd}')
            output = self.client.cmd(f"timeout {timeout} {cmd}")

        result = []
        def parse_result(line):
            if 'complete' not in line:
                return
            try:
                match = re.search(r'\d+\.\d+ seconds', line).group(0)
                time_s = float(match.split(' ')[0])
                result.append(time_s)
            except:
                pass

        print(output)
        for line in output.split('\n'):
            parse_result(line)

        # TODO figure out why popen isn't working
        # logfile = self.logfile(self.client)
        # timeout_flag = self.net.popen(self.client, cmd, background=False,
        #     console_logger=DEBUG, logfile=logfile, func=parse_result,
        #     timeout=timeout, raise_error=False)

        if len(result) == 0:
            WARN('PicoQUIC client failed to return result')
            if timeout is not None:
                WARN('assuming picoquic timeout')
                return (HTTP_TIMEOUT_STATUSCODE, timeout)
            else:
                return None
        elif len(result) > 1:
            WARN(f'PicoQUIC client returned multiple results {result}')
        else:
            return (HTTP_OK_STATUSCODE, result[0])
