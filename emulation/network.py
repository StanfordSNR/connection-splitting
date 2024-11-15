import subprocess
import sys
import threading

from common import *
from mininet.net import Mininet
from mininet.link import TCLink


"""
Defines an emulated network in mininet with one intermediate hop between the
client and the server. The 1st link is between the client / data receiver (h1)
and the router (r1), and the 2nd link is between the router (r1) and the
server / data sender (h2).
"""
class OneHopNetwork:
    METRICS = ['tx_packets', 'tx_bytes', 'rx_packets', 'rx_bytes']

    def __init__(self, delay1, delay2, loss1, loss2, bw1, bw2):
        self.net = Mininet(controller=None, link=TCLink)

        # Add hosts and switches
        self.h1 = self.net.addHost('h1', ip=OneHopNetwork._ip(1),
                                   mac=OneHopNetwork._mac(1))
        self.h2 = self.net.addHost('h2', ip=OneHopNetwork._ip(2),
                                   mac=OneHopNetwork._mac(2))
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
        bdp = OneHopNetwork._calculate_bdp(delay1, delay2, bw1, bw2)
        self._config_iface('h1-eth0', delay1, loss1, bw1, bdp)
        self._config_iface('r1-eth0', delay1, loss1, bw1, bdp)
        self._config_iface('r1-eth1', delay2, loss2, bw2, bdp)
        self._config_iface('h2-eth0', delay2, loss2, bw2, bdp)

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

    def _config_iface(self, iface, delay, loss, bw, bdp, gso=True, tso=True):
        host = self.iface_to_host[iface]
        self.popen(host, f'tc qdisc add dev {iface} root handle 2: ' \
                         f'netem loss {loss}% delay {delay}ms')
        self.popen(host, f'tc qdisc add dev {iface} parent 2: handle 3: ' \
                         f'htb default 10')
        self.popen(host, f'tc class add dev {iface} parent 3: ' \
                         f'classid 10 htb rate {bw}Mbit')
        self.popen(host, f'tc qdisc add dev {iface} parent 3:10 handle 11: ' \
                         f'red limit {bdp*4} avpkt 1000 ' \
                         f'adaptive harddrop bandwidth {bw}Mbit')

        # Turn off tso and gso to send MTU-sized packets
        gso = 'on' if gso else 'off'
        tso = 'on' if tso else 'off'
        self.popen(host, f'ethtool -K {iface} gso {gso} tso {tso}')

    def set_tcp_congestion_control(self, cca):
        assert cca in ['cubic', 'bbr']
        cmd = f'sudo sysctl -w net.ipv4.tcp_congestion_control={cca}'
        self.popen(None, cmd, stderr=False, console_logger=DEBUG)

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
        for metric in OneHopNetwork.METRICS:
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
            for metric in OneHopNetwork.METRICS:
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

    def popen(self, host, cmd, background=False, func=None,
              stdout=False, stderr=True, console_logger=TRACE, logfile=None):
        """
        Start a process that executes a command on the given mininet host.
        Parameters:
        - host: the mininet host
        - cmd: a command string
        - background: whether to run as a background process
        - func: a function to execute on every line of output.
          the function takes as input (line,).
        - stdout: whether to log stdout to the console
        - stderr: whether to log stderr to the console
        - console_logger: log level function for logging to the console
        - logfile: the logfile to append output (both stdout and stderr) to
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

        # Execute the command on a mininet host
        p = host.popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if background:
            self.background_processes.append(p)
            thread = threading.Thread(
                target=handle_background_process,
                args=(p, logfile, func),
            )
            thread.start()
            return p
        else:
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
            exitcode = p.wait()
            if exitcode != 0:
                print(f'{host}({cmd}) = {exitcode}', file=sys.stderr)
                exit(1)

    def stop(self):
        for p in self.background_processes:
            p.terminate()
            p.wait()
        if self.net is not None:
            self.net.stop()
