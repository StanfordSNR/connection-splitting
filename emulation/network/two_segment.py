from common import *
from network import EmulatedNetwork


class TwoSegmentNetwork(EmulatedNetwork):
    """
    Defines an emulated network in mininet with one intermediate hop between the
    client and the server. The 1st link is between the client / data receiver
    (h1) and the router (r1), and the 2nd link is between the router (r1) and
    the server / data sender (h2).
    """
    def __init__(self, delay1, delay2, loss1, loss2, bw1, bw2, qdisc, pacing):
        super().__init__()

        # Add hosts, switches, and network emulation nodes
        self.h1 = self.net.addHost('h1', ip='172.16.1.10/24', mac=mac(1))
        self.h2 = self.net.addHost('h2', ip='172.16.2.10/24', mac=mac(2))
        self.r1 = self.net.addHost('r1')
        self.e1 = self.net.addHost('e1')
        self.e2 = self.net.addHost('e2')

        # Add links
        self.net.addLink(self.h1, self.e1)
        self.net.addLink(self.e1, self.r1)
        self.net.addLink(self.r1, self.e2)
        self.net.addLink(self.e2, self.h2)
        self.net.build()

        # Initialize statistics
        self.iface_to_host = {
            'h1-eth0': self.h1,
            'r1-eth0': self.r1,
            'r1-eth1': self.r1,
            'h2-eth0': self.h2,
            'e1-eth0': self.e1,
            'e1-eth1': self.e1,
            'e2-eth0': self.e2,
            'e2-eth1': self.e2,
        }

        # Setup routing and forwarding
        self.popen(self.r1, "ifconfig r1-eth0 0")
        self.popen(self.r1, "ifconfig r1-eth1 0")
        self.popen(self.r1, "ifconfig r1-eth0 hw ether 00:00:00:00:01:01")
        self.popen(self.r1, "ifconfig r1-eth1 hw ether 00:00:00:00:01:02")
        self.popen(self.r1, "ip addr add 172.16.1.1/24 brd + dev r1-eth0")
        self.popen(self.r1, "ip addr add 172.16.2.1/24 brd + dev r1-eth1")
        self.r1.cmd("echo 1 > /proc/sys/net/ipv4/ip_forward")
        self.popen(self.h1, "ip route add 172.16.2.0/24 via 172.16.1.1")
        self.popen(self.h2, "ip route add 172.16.1.0/24 via 172.16.2.1")

        # Set up bridging on the network emulation nodes
        self.popen(self.e1, "brctl addbr br0")
        self.popen(self.e1, "brctl addif br0 e1-eth0")
        self.popen(self.e1, "brctl addif br0 e1-eth1")
        self.popen(self.e1, "ip link set dev br0 up")
        self.popen(self.e2, "brctl addbr br0")
        self.popen(self.e2, "brctl addif br0 e2-eth0")
        self.popen(self.e2, "brctl addif br0 e2-eth1")
        self.popen(self.e2, "ip link set dev br0 up")

        # Configure link latency, delay, bandwidth, and queue size
        # https://unix.stackexchange.com/questions/100785/bucket-size-in-tbf
        rtt = 2 * (delay1 + delay2)
        bdp = calculate_bdp(delay1, delay2, bw1, bw2)
        self.config_iface('h1-eth0', False, pacing)
        self.config_iface('r1-eth0', False, pacing)
        self.config_iface('r1-eth1', False, pacing)
        self.config_iface('h2-eth0', False, pacing)
        self.config_iface('e1-eth0', True, False, delay1, loss1, bw1, bdp, qdisc)
        self.config_iface('e1-eth1', True, False, delay1, loss1, bw1, bdp, qdisc)
        self.config_iface('e2-eth0', True, False, delay2, loss2, bw2, bdp, qdisc)
        self.config_iface('e2-eth1', True, False, delay2, loss2, bw2, bdp, qdisc)
