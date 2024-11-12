import select
import subprocess
import sys

from common import *
from mininet.net import Mininet
from mininet.link import TCLink


class NetStatistics():
    def __init__(self, iface_to_host):
        self.iface_to_host = iface_to_host
        self.tx_packets = {}
        self.tx_bytes = {}
        self.rx_packets = {}
        self.rx_bytes = {}

    def get(self, host, iface, name):
        p = host.popen(['cat', f'/sys/class/net/{iface}/statistics/{name}'])
        assert p.wait() == 0
        for line in p.stdout:
            return int(line.strip())

    def start(self):
        for iface, host in self.iface_to_host.items():
            self.tx_packets[iface] = self.get(host, iface, 'tx_packets')
            self.tx_bytes[iface] = self.get(host, iface, 'tx_bytes')
            self.rx_packets[iface] = self.get(host, iface, 'rx_packets')
            self.rx_bytes[iface] = self.get(host, iface, 'rx_bytes')

    def stop_and_print(self):
        # ifaces = self.iface_to_host.keys()
        iface_to_str = {
            'h2-eth0': 'DS->proxy',
            'r1-eth1': 'DS<-proxy',
            'r1-eth0': 'proxy->DR',
            'h1-eth0': 'proxy<-DR'
        }
        INFO('            tx_packets    tx_bytes  rx_packets    rx_bytes')
        for iface in ['h2-eth0', 'r1-eth1', 'r1-eth0', 'h1-eth0']:
            host = self.iface_to_host[iface]
            tx_packets = self.get(host, iface, 'tx_packets') - self.tx_packets[iface]
            tx_bytes = self.get(host, iface, 'tx_bytes') - self.tx_bytes[iface]
            rx_packets = self.get(host, iface, 'rx_packets') - self.rx_packets[iface]
            rx_bytes = self.get(host, iface, 'rx_bytes') - self.rx_bytes[iface]
            INFO(f'{iface_to_str[iface]:<10}{tx_packets:>12}{tx_bytes:>12}{rx_packets:>12}{rx_bytes:>12}')


"""
Defines an emulated network in mininet with one intermediate hop between the
client and the server. The 1st link is between the client / data receiver (h1)
and the router (r1), and the 2nd link is between the router (r1) and the
server / data sender (h2).
"""
class OneHopNetwork:
    def __init__(self, delay1, delay2, loss1, loss2, bw1, bw2, statistics=False):
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
        if statistics:
            self.statistics = NetStatistics(iface_to_host)
        else:
            self.statistics = None

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

    def popen(self, host, cmd, background=False, logger=TRACE,
              stdout=False, stderr=True):
        # Log the command to be executed
        host_str = '' if host is None else f'{host.name} '
        background_str = ' &' if background else ''
        logger(f'{host_str}{cmd}{background_str}')

        # Execute the command on the local host
        if host is None:
            assert not background
            p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            if p.stdout:
                print(p.stdout.strip(), end='', file=sys.stdout)
            if p.stderr:
                print(p.stderr.strip(), end='', file=sys.stderr)
            if p.returncode != 0:
                print(f'{cmd} = {p.returncode}', file=sys.stderr)
                exit(1)
            return

        # Execute the command on a mininet host
        p = host.popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if background:
            self.background_processes.append(p)
            return p
        else:
            while p.poll() is None or p.stdout.peek() or p.stderr.peek():
                ready, _, _ = select.select([p.stdout, p.stderr], [], [])
                for stream in ready:
                    line = stream.readline()
                    if not line:
                        continue
                    if stream == p.stdout and stdout:
                        print(line.decode(), end='', file=sys.stdout)
                    if stream == p.stderr and stderr:
                        print(line.decode(), end='', file=sys.stderr)
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
