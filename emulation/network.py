import subprocess
import sys
import threading

from common import *
from mininet.net import Mininet
from mininet.link import TCLink


"""
Defines a basic network in Mininet with two hosts, h1 and h2.
"""
class EmulatedNetwork:
    METRICS = ['tx_packets', 'tx_bytes', 'rx_packets', 'rx_bytes']

    def __init__(self):
        self.net = Mininet(controller=None, link=TCLink)
        self.iface_to_host = {}

        # Keep track of background processes for cleanup
        self.background_processes = []

    @staticmethod
    def _mac(digit):
        assert 0 <= digit < 10
        return f'00:00:00:00:00:0{int(digit)}'

    @staticmethod
    def _ip(digit):
        assert 0 <= digit < 10
        return f'10.0.{int(digit)}.10/24'

    @staticmethod
    def _calculate_bdp(delay1, delay2, bw1, bw2):
        rtt_ms = 2 * (delay1 + delay2)
        bw_mbps = min(bw1, bw2)
        return rtt_ms * bw_mbps * 1000000. / 1000. / 8.

    def _config_iface(self, iface, delay, loss, bw, bdp, gso=True, tso=True,
                      jitter=None):
        """Configures the given interface <iface>:
        - Loss: <loss>% stochastic packet loss
        - Delay: <delay>ms delay w/ ±<jitter>ms jitter, <delay_corr>% correlation
        - Base bandwidth: <bw> Mbit/s, range: <bw_min> to <bw_max> Mbit/s
        - Bandwidth-delay product: <bdp> is used to set the queue size
        """
        host = self.iface_to_host[iface]

        # Add netem with delay variability
        cmd = f'tc qdisc add dev {iface} root handle 2: '\
              f'netem loss {loss}% delay {delay}ms '
        if jitter is not None:
            cmd += f'{jitter}ms {DEFAULT_DELAY_CORR}% distribution paretonormal'
        self.popen(host, cmd)

        # Add HTB for bandwidth
        # Take the min because sch_htb complains about the quantum being too big
        # past 200,000 bytes. Otherwise calculate using the default r2q.
        r2q = 10
        quantum = min(int(bw*1000000/8 / r2q), 200000)
        self.popen(host, f'tc qdisc add dev {iface} parent 2: handle 3: ' \
                         f'htb default 10')
        self.popen(host, f'tc class add dev {iface} parent 3: ' \
                         f'classid 10 htb rate {bw}Mbit quantum {quantum}')

        # Add RED for queue management
        # The harddrop byte limit needs to be a minimum value or RED will be
        # unable to calculate the EWMA constant so that min >= avpkt
        limit = max(int(bdp*4), 1000*3*4*4)
        qmax = int(limit/4)
        qmin = int(qmax/3)
        avpkt = 1000
        # RED: WARNING. Burst (2*min+max)/(3*avpkt) seems to be too large.
        # RTNETLINK answers: Invalid argument
        burst = int(1 + qmin / avpkt)
        self.popen(host, f'tc qdisc add dev {iface} parent 3:10 handle 11: ' \
                         f'red limit {limit} avpkt {avpkt} ' \
                         f'adaptive harddrop bandwidth {bw}Mbit burst {burst}', console_logger=WARN)

        # Turn off tso and gso to send MTU-sized packets
        gso = 'on' if gso else 'off'
        tso = 'on' if tso else 'off'
        self.popen(host, f'ethtool -K {iface} gso {gso} tso {tso}')

    def set_tcp_congestion_control(self, cca):
        assert cca in ['cubic', 'bbr']
        for host in self.net.hosts:
            cmd = f'sudo sysctl -w net.ipv4.tcp_congestion_control={cca}'
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
              stdout=False, stderr=True, console_logger=TRACE, logfile=None):
        """
        Start a process that executes a command on the given mininet host.
        Parameters:
        - host: the mininet host
        - cmd: a command string
        - background: whether to run as a background process
        - func: a function to execute on every line of output.
          the function takes as input (line,).
        - timeout: timeout, in seconds, to use on a mininet host
        - stdout: whether to log stdout to the console
        - stderr: whether to log stderr to the console
        - console_logger: log level function for logging to the console
        - logfile: the logfile to append output (both stdout and stderr) to

        Returns:
        - If a background process, returns the background process.
        - If not, returns True if there was a timeout and False if the process
          executed successfully.
        - For any other exitcodes, exits the program.
        """
        # Log the command to be executed
        host_str = '' if host is None else f'{host.name} '
        background_str = ' &' if background else ''
        console_logger(f'{host_str}{cmd}{background_str}')

        # Execute the command on the local host
        if host is None:
            assert not background
            p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            if p.stdout and stdout:
                print(p.stdout.strip(), file=sys.stderr)
            if p.stderr and stderr:
                print(p.stderr.strip(), file=sys.stderr)
            if p.returncode != 0:
                print(f'{cmd} = {p.returncode}', file=sys.stderr)
                exit(1)
            return

        # Execute the command on a mininet host in the background
        if background:
            p = host.popen(cmd.split(), stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, text=True)
            self.background_processes.append(p)
            thread = threading.Thread(
                target=handle_background_process,
                args=(p, logfile, func),
            )
            thread.start()
            return p

        # Execute the command synchronously with a timeout
        cmd_input = cmd.split()
        if timeout is not None:
            cmd_input = ['timeout', f'{timeout}s'] + cmd_input
        p = host.popen(cmd_input, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, text=True)
        for line, stream in read_subprocess_pipe(p):
            if stream == p.stdout and stdout:
                print(line, end='', file=sys.stderr)
            if stream == p.stderr and stderr:
                print(line, end='', file=sys.stderr)
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
            print(f'{host}({cmd}) = {exitcode}', file=sys.stderr)
            exit(1)

    def stop(self):
        for p in self.background_processes:
            p.terminate()
            p.wait()
        if self.net is not None:
            self.net.stop()


"""
Defines an emulated network in mininet with one intermediate hop between the
client and the server. The 1st link is between the client / data receiver (h1)
and the router (r1), and the 2nd link is between the router (r1) and the
server / data sender (h2).
"""
class OneHopNetwork(EmulatedNetwork):
    def __init__(self, delay1, delay2, loss1, loss2, bw1, bw2, jitter1, jitter2):
        super().__init__()

        # Add hosts and switches
        self.h1 = self.net.addHost('h1', ip=self._ip(1),
                                   mac=self._mac(1))
        self.h2 = self.net.addHost('h2', ip=self._ip(2),
                                   mac=self._mac(2))
        self.r1 = self.net.addHost('r1')

        # Add links
        self.net.addLink(self.r1, self.h1)
        self.net.addLink(self.r1, self.h2)
        self.net.build()

        # Initialize statistics
        self.iface_to_host = {
            'h1-eth0': self.h1,
            'r1-eth0': self.r1,
            'r1-eth1': self.r1,
            'h2-eth0': self.h2
        }

        # Setup routing and forwarding
        self.popen(self.r1, "ifconfig r1-eth0 0")
        self.popen(self.r1, "ifconfig r1-eth1 0")
        self.popen(self.r1, "ifconfig r1-eth0 hw ether 00:00:00:00:01:01")
        self.popen(self.r1, "ifconfig r1-eth1 hw ether 00:00:00:00:01:02")
        self.popen(self.r1, "ip addr add 10.0.1.1/24 brd + dev r1-eth0")
        self.popen(self.r1, "ip addr add 10.0.2.1/24 brd + dev r1-eth1")
        self.r1.cmd("echo 1 > /proc/sys/net/ipv4/ip_forward")
        self.popen(self.h1, "ip route add default via 10.0.1.1")
        self.popen(self.h2, "ip route add default via 10.0.2.1")

        # Configure link latency, delay, bandwidth, and queue size
        # https://unix.stackexchange.com/questions/100785/bucket-size-in-tbf
        bdp = self._calculate_bdp(delay1, delay2, bw1, bw2)
        self._config_iface('h1-eth0', delay1, loss1, bw1, bdp, jitter=jitter1)
        self._config_iface('r1-eth0', delay1, loss1, bw1, bdp, jitter=jitter1)
        self._config_iface('r1-eth1', delay2, loss2, bw2, bdp, jitter=jitter2)
        self._config_iface('h2-eth0', delay2, loss2, bw2, bdp, jitter=jitter2)


"""
Defines an emulated network in mininet that directly connects the client /
data receiver (h1) to the server / data sender (h2) with a single link.
"""
class DirectNetwork(EmulatedNetwork):
    def __init__(self, delay, loss, bw, jitter):
        super().__init__()

        # Add hosts and switches
        self.h1 = self.net.addHost('h1', ip=self._ip(1),
                                   mac=self._mac(1))
        self.h2 = self.net.addHost('h2', ip=self._ip(2),
                                   mac=self._mac(2))

        # Add link
        self.net.addLink(self.h1, self.h2)
        self.net.build()

        # Initialize statistics
        self.iface_to_host = {
            'h1-eth0': self.h1,
            'h2-eth0': self.h2,
        }

        # Setup routing
        self.popen(self.h1, "ip route add default via 10.0.1.10")
        self.popen(self.h2, "ip route add default via 10.0.2.10")

        # Configure link latency, delay, bandwidth, and queue size
        # https://unix.stackexchange.com/questions/100785/bucket-size-in-tbf
        bdp = self._calculate_bdp(delay, 0, bw, bw)
        self._config_iface('h1-eth0', delay, loss, bw, bdp, jitter=jitter)
        self._config_iface('h2-eth0', delay, loss, bw, bdp, jitter=jitter)
