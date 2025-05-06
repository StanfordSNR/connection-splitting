import subprocess
import sys
import threading

from common import *
from mininet.node import Host
from mininet.net import Mininet
from mininet.link import TCLink


class EmulatedNetwork:
    """
    Defines a basic network in Mininet with two hosts, h1 and h2.
    """
    METRICS = ['tx_packets', 'tx_bytes', 'rx_packets', 'rx_bytes']

    def __init__(self, debug: bool=False):
        self.net = Mininet(controller=None, link=TCLink)
        self.debug = debug
        self.primary_ifaces = []
        self.iface_to_host = {}

        # Keep track of background processes for cleanup
        self.background_processes = []
        self.background_threads = []

    def set_arp_table(self, host: Host, ip: str, mac: str, iface: str):
        self.popen(host, f'ip neigh add {ip} lladdr {mac} dev {iface} nud permanent')

    def start_tcpdump(self, logdir: str):
        for iface in self.primary_ifaces:
            host = self.iface_to_host[iface]
            cmd = f'tcpdump -i {iface} -w {logdir}/{iface}.pcap'
            self.popen(host, cmd, background=True, console_logger=DEBUG)

    def config_iface(self, iface, netem: bool, pacing: bool=False,
                      delay=None, loss=None, bw=None, bdp=None, qdisc=None,
                      gso=True, tso=True):
        """Configures the given interface <iface>:
        - Netem: whether this is a network emulation node (i.e., delay, loss, etc.
          should be configured)
        - Loss: <loss>% stochastic packet loss
        - Delay: <delay>ms delay
        - Base bandwidth: <bw> Mbit/s, range: <bw_min> to <bw_max> Mbit/s
        - Bandwidth-delay product: <bdp> is used to set the queue size
        """
        host = self.iface_to_host[iface]

        # Configure the end-host or router
        if not netem:
            # BBR requires fq (with pacing) for kernel versions <v4.20
            # https://groups.google.com/g/bbr-dev/c/zZ5c0qkWqbo/m/QulUwXLZAQAJ
            linux_version = get_linux_version()
            if pacing or linux_version < 5.0:
                self.popen(host, f'tc qdisc add dev {iface} root handle 2: '\
                                f'fq pacing', console_logger=TRACE)
            return

        # Configure the network emulator node

        # Add netem with delay variability
        cmd = f'tc qdisc add dev {iface} root handle 2: '\
              f'netem delay {delay}ms '
        if loss is not None and int(loss) > 0:
            cmd += f'loss {loss}% '
        self.popen(host, cmd, console_logger=TRACE)

        # Add HTB for bandwidth
        # Take the min because sch_htb complains about the quantum being too big
        # past 200,000 bytes. Otherwise calculate using the default r2q.
        # If using a policer at the proxy, make the bandwidth of the links
        # twice as high as the policed rate.
        r2q = 10
        quantum = min(int(bw*1000000/8 / r2q), 200000)
        self.popen(host, f'tc qdisc add dev {iface} parent 2: handle 3: ' \
                         f'htb default 10', console_logger=TRACE)
        htb_rate = int(2*bw) if qdisc == 'policer' else bw
        self.popen(host, f'tc class add dev {iface} parent 3: ' \
                         f'classid 10 htb rate {htb_rate}Mbit quantum {quantum}',
                         console_logger=TRACE)

        # Add queue management
        if qdisc == 'policer':
            # Burst time of 10ms
            burst = int(bw * 10 * 1000 / 8)
            queue_cmd = f'tc filter add dev {iface} parent 3: '\
                        f'protocol ip u32 match ip src 0.0.0.0/0 '\
                        f'action police rate {bw}mbit burst {burst} '\
                        f'conform-exceed drop'
            self.popen(host, queue_cmd, console_logger=DEBUG)
        elif qdisc is not None:
            queue_cmd = f'tc qdisc add dev {iface} parent 3:10 handle 11: '
            if qdisc == 'red':
                # The harddrop byte limit needs to be a min value or RED will
                # be unable to calculate the EWMA constant so that min >= avpkt
                limit = max(int(bdp*4), 1000*3*4*4)
                qmax = int(limit/4)
                qmin = int(qmax/3)
                avpkt = 1000
                # RED: WARNING. Burst (2*min+max)/(3*avpkt) seems to be too large.
                # RTNETLINK answers: Invalid argument
                burst = int(1 + qmin / avpkt)
                queue_cmd += f'red limit {limit} avpkt {avpkt} ' \
                             f'adaptive harddrop ' \
                             f'bandwidth {bw}Mbit burst {burst}'
            elif qdisc == 'bfifo-large':
                queue_cmd += f'bfifo limit {bdp}' # BDP
            elif qdisc == 'bfifo-small':
                limit = max(1500, int(0.1 * bdp)) # min(mtu, 0.1*BDP)
                queue_cmd += f'bfifo limit {limit}'
            elif qdisc == 'pie':
                # Memory limit, since packets are dropped based on target delay
                limit = int(4 * bdp / 1500)
                queue_cmd +=      f'pie limit {limit}'
            elif qdisc == 'codel':
                # Memory limit, since packets are dropped based on target delay
                limit = int(4 * bdp / 1500)
                queue_cmd += f'codel limit {limit} interval {rtt}ms'
            elif qdisc == 'fq_codel':
                queue_cmd += f'fq_codel'
            else:
                raise NotImplementedError(qdisc)
            self.popen(host, queue_cmd, console_logger=TRACE)

        # Turn off tso and gso to send MTU-sized packets
        gso = 'on' if gso else 'off'
        tso = 'on' if tso else 'off'
        self.popen(host, f'ethtool -K {iface} gso {gso} tso {tso}',
                   console_logger=TRACE)

    def set_tcp_congestion_control(self, cca):
        version = get_linux_version()
        cmd = f'sysctl -w net.ipv4.tcp_congestion_control={cca}'
        if version == 4.9 or version < 4.15:
            # Setting CCA on Mininet nodes will fail for kernel v4.9-4.14, but they
            # will inherit the CCA setting of the host.
            self.popen(None, cmd, stderr=True, console_logger=DEBUG)
        else:
            for host in self.net.hosts:
                self.popen(host, cmd, stderr=False, console_logger=DEBUG)

    def reset_statistics(self):
        """After a reset, an immediate snapshot would return all 0 values.
        """
        self.raw_metrics = self._read_raw_metrics()

    def snapshot_statistics(self):
        """Return a snapshot of metrics since the last reset. This is a
        difference from the statistics on reset.
        """
        now = self._read_raw_metrics()
        snapshot = {'ifaces': list(sorted(self.iface_to_host.keys()))}
        for metric in self.METRICS:
            snapshot[metric] = []
            for iface in snapshot['ifaces']:
                statistic = now[iface][metric] - self.raw_metrics[iface][metric]
                snapshot[metric].append(statistic)
        return snapshot

    def _read_raw_metrics(self):
        """Read the current raw metrics.
        """
        stats = {}
        for iface in self.iface_to_host:
            stats[iface] = {}
            for metric in self.METRICS:
                stats[iface][metric] = self._read_raw_metric(iface, metric)
        return stats

    def _read_raw_metric(self, iface, metric):
        """Read a single raw metric.
        """
        value = []
        def append_value(line):
            value.append(int(line.strip()))
        cmd = f'cat /sys/class/net/{iface}/statistics/{metric}'
        host = self.iface_to_host[iface]
        self.popen(host, cmd, func=append_value)
        if len(value) == 0:
            ERROR(f'failed to get metric {iface} {metric}')
            return 0
        else:
            return value[0]

    def popen(self, host, cmd, background=False, func=None, timeout=None,
              stdout=False, stderr=True, console_logger=TRACE, logfile=None,
              raise_error=True):
        """
        Start a process that executes a command on the given mininet host.

        The function has a variety of logging capabilities. All commands can
        be logged to the console using the console_logger. Only synchronous
        processes can log outputs to the console, and console output can be
        quieted using the stdout and/or stderr options. Only mininet host
        commands can log to a logfile, and if provided, all output is logged.
        Errors are always logged to the console, though processes can be
        configured to error without raising an exception.

        Parameters:
        - host: The mininet host, or None if executing on the local host.
        - cmd: A command string.
        - background: Whether to run as a background process. Background
          processes can only be executed on mininet hosts.
        - func: A callback function to execute on every line of output. The
          function takes as input (line,). Only on mininet hosts.
        - timeout: The cmd timeout, in seconds. Only on mininet hosts and
          synchronous processes.

        Logging parameters:
        - console_logger: Log level function, e.g., DEBUG, for logging to the
          console. Takes a string as input and logs the executed command,
          appending ' &' if it is a background process and prepending the host
          name if it is executed on a mininet host. Also logs stdout and/or
          stderr, whichever is enabled, for synchronous processes.
        - stdout: Whether to log stdout to the console logger.
        - stderr: Whether to log stderr to the console logger.
        - logfile: The name of the logfile to append full output (both stdout
          and stderr). Independent of the stdout and stderr options. Only on
          mininet hosts. If the network collects perf reports, the report will
          be written to "<logfile>.perf".
        - raise_error: Whether to raise an error on a non-zero exitcode or to
          fail silently with only a log message. Only on synchronous processes
          as we don't wait for background processes to terminate to check the
          exitcode.

        Returns:
        - If a background process, returns the process and the thread that is
          handling the background process.
        - If not, returns True if there was a timeout and False if the process
          executed to completion.
        - For non-zero exitcodes, exits the program unless configured not to.

        Raises:
        AssertionError on a valid configuration i.e., timeouts are enabled for
        a process that is not executed on a mininet host.
        """
        # Log the command to be executed
        host_str = '' if host is None else f'{host.name} '
        background_str = ' &' if background else ''
        console_logger(f'{host_str}{cmd}{background_str}')

        # Set debug environment variables.
        env = os.environ.copy()
        env['RUST_BACKTRACE'] = '1'
        if self.debug:
            env['RUST_LOG'] = 'debug'
        else:
            env['RUST_LOG'] = 'info'

        # Execute the command on the local host
        if host is None:
            assert not background
            assert timeout is None
            assert logfile is None
            assert func is None
            p = subprocess.run(cmd, shell=True, text=True, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if p.stdout and stdout:
                console_logger(p.stdout.strip())
            if p.stderr and stderr:
                console_logger(p.stderr.strip())
            if p.returncode != 0:
                ERROR(f'{cmd} = {p.returncode}')
                if raise_error:
                    raise ValueError(f'{cmd} = {p.returncode}')
            return

        # Execute the command on a mininet host in the background
        if background:
            assert timeout is None
            p = host.popen(cmd.split(), stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, text=True, env=env)
            thread = threading.Thread(
                target=handle_background_process,
                args=(p, logfile, func),
            )
            thread.start()
            self.background_processes.append(p)
            self.background_threads.append(thread)
            return (p, thread)

        # Execute the command synchronously, possibly with a timeout
        cmd_input = cmd.split()
        if timeout is not None:
            cmd_input = ['timeout', f'{timeout}s'] + cmd_input
        p = host.popen(cmd_input, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, text=True, env=env)
        for line, stream in read_subprocess_pipe(p):
            if stream == p.stdout and stdout:
                console_logger(line.strip())
            if stream == p.stderr and stderr:
                console_logger(line.strip())
            if logfile is not None:
                with open(logfile, 'a') as f:
                    f.write(line)
            if func is not None:
                func(line)

        # Handle the exitcode
        exitcode = p.wait()
        if exitcode == 0:
            return False
        elif exitcode == LINUX_TIMEOUT_EXITCODE:
            return True
        else:
            ERROR(f'{host}({cmd}) = {exitcode}')
            if raise_error:
                debug_str = f'{host}({cmd}) = {p.returncode}'
                raise ValueError(debug_str)

    def stop(self):
        for p in self.background_processes:
            p.terminate()
            p.wait()
        if self.net is not None:
            self.net.stop()


from .one_segment import OneSegmentNetwork
from .two_segment import TwoSegmentNetwork
