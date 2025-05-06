from abc import ABC, abstractmethod
from typing import Optional, Tuple

import mininet

from network import EmulatedNetwork
from result import BenchmarkResult
from common import *


class Benchmark(ABC):
    def __init__(
        self, net: EmulatedNetwork, protocol: Protocol, label: str,
        logdir: str, n: str, cca: str, certfile: str, keyfile: str, pep: bool,
    ):
        """
        File download benchmark where the HTTP client on the h1 host requests
        a certain number of application-layer bytes from the HTTP server on
        the h2 host. Reports metrics such as the request latency and throughput.

        Subclasses of Benchmark must call this constructor.

        Parameters:
        - net: The mininet network to run the benchmark on. Requires an h1 and
          h2 host, and a p1 host if a proxy is configured.
        - protocol: The transport protocol implementation.
        - label: The unique label to associate with this configuration.
        - logdir: Path to a log directory (that already exists). The logs are
          written to the SERVER_LOGFILE, CLIENT_LOGFILE, and ROUTER_LOGFILE
          files in this directory, as defined in common.py.
        - n: The data size, in bytes, transferred in the
          application-layer data of the GET request. Excludes HTTP headers.
        - cca: The congestion control algorithm used in the transport protocol.
        - certfile: Path to the TLS/SSL certificate file.
        - keyfile: Path to the TLS/SSL key file.
        - pep: Whether to start a TCP connection-splitting PEP on p1.
        """
        self.net = net
        self.protocol = protocol
        self.label = label
        self.logdir = logdir
        self.n = n
        self.cca = cca
        self.certfile = certfile
        self.keyfile = keyfile
        self.pep = pep

    def logfile(self, host: mininet.node.Host) -> Optional[str]:
        """Path to the logfile for this host. The logs are written to the
        SERVER_LOGFILE, CLIENT_LOGFILE, and ROUTER_LOGFILE files, as defined in
        common.py, in the provided log directory.
        """
        if host == self.server:
            return f'{self.logdir}/{SERVER_LOGFILE}'
        elif host == self.client:
            return f'{self.logdir}/{CLIENT_LOGFILE}'
        elif host == self.proxy and self.proxy is not None:
            return f'{self.logdir}/{ROUTER_LOGFILE}'

    @property
    def server(self):
        return self.net.h2

    @property
    def client(self):
        return self.net.h1

    @abstractmethod
    def start_server(self, timeout: int=SETUP_TIMEOUT):
        """Start the HTTP server on the h2 host and write output to a logfile.

        This function runs the server in the background but blocks until the
        server is ready to accept requests. Raises an error if unsuccessful.

        Parameters:
        - timeout: The number of seconds to block during setup before an error.
        """
        pass

    @abstractmethod
    def run_client(
        self, timeout: Optional[int]=None,
    ) -> Optional[Tuple[int, float]]:
        """
        Runs the HTTP client on the h1 host and writes output to a logfile.

        Parameters:
        - timeout: If provided, the number of seconds to wait for the client
          to complete its request.

        Returns:
        - If there is an error that is not a timeout, returns None.
        - The HTTP status code and the total runtime, in seconds, of the GET
          request. If the client has timed out, returns HTTP_TIMEOUT_STATUSCODE
          even though the timeout may not have occurred in the actual endpoints.
        """
        pass

    def run_benchmark(
        self, num_trials: int, timeout: Optional[int]=None,
        network_statistics: bool=False,
    ) -> BenchmarkResult:
        """
        Running the benchmark will start the HTTP server on the h2 host and
        the HTTP client on the h1 host, the latter as many times as the number
        of trials.

        Parameters:
        - num_trials: Number of trials.
        - timeout: If provided, the number of seconds to wait for each client
          to complete its request.
        - network_statistics: Whether to collect network statistics, i.e., the
          number of bytes and packets that were sent and received at each
          interface, of the most recent trial.

        Returns:
        - A BenchmarkResult corresponding to the result of this benchmark.
        """
        self.start_server()

        # Initialize the benchmark result
        result = BenchmarkResult(
            label=self.label,
            protocol=self.protocol.name,
            data_size=self.n,
            cca=self.cca,
            pep=self.pep,
        )

        # Run the client
        for _ in range(num_trials):
            result.append_new_output()
            self.net.reset_statistics()
            output = self.run_client(timeout=timeout)
            if network_statistics:
                statistics = self.net.snapshot_statistics()
                result.set_network_statistics(statistics)

            # Handle an error in the client
            if output is None:
                result.set_success(False)
                result.set_timeout(False)
                continue

            # Handle a successful trial
            status_code, time_s = output
            result.set_success(status_code == HTTP_OK_STATUSCODE)
            result.set_timeout(status_code == HTTP_TIMEOUT_STATUSCODE)
            result.set_time_s(time_s)

        # Return the result
        return result


from .cloudflare import CloudflareQUICBenchmark
from .google import GoogleQUICBenchmark
from .picoquic import PicoQUICBenchmark
from .tcp import LinuxTCPBenchmark
