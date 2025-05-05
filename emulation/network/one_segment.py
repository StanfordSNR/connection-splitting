from common import *
from network import EmulatedNetwork


class OneSegmentNetwork(EmulatedNetwork):
    """
    Defines an emulated network in mininet that directly connects the client /
    data receiver (h1) to the server / data sender (h2) with a single link.
    """
    def __init__(self, delay, loss, bw, qdisc, pacing):
        super().__init__()

        # Add hosts and switches
        self.h1 = self.net.addHost('h1', ip='172.16.1.10/24', mac=mac(1))
        self.h2 = self.net.addHost('h2', ip='172.16.2.10/24', mac=mac(2))
        self.e1 = self.net.addHost('e1')

        # Add link
        self.net.addLink(self.h1, self.e1)
        self.net.addLink(self.e1, self.h2)
        self.net.build()

        # Initialize statistics
        self.primary_ifaces = ['h1-eth0', 'h2-eth0']
        self.iface_to_host = {
            'h1-eth0': self.h1,
            'h2-eth0': self.h2,
            'e1-eth0': self.e1,
            'e1-eth1': self.e1,
        }

        # Setup routing
        self.popen(self.h1, "ip route add 172.16.2.0/24 via 172.16.1.10")
        self.popen(self.h2, "ip route add 172.16.1.0/24 via 172.16.2.10")
        # Bridging on the network emulation nodes
        self.popen(self.e1, "brctl addbr br0")
        self.popen(self.e1, "brctl addif br0 e1-eth0")
        self.popen(self.e1, "brctl addif br0 e1-eth1")
        self.popen(self.e1, "ip link set dev br0 up")

        # Prepopulate arp table
        self.set_arp_table(self.h1, '172.16.2.10', mac(2), 'h1-eth0')
        self.set_arp_table(self.h2, '172.16.1.10', mac(1), 'h2-eth0')

        # Configure link latency, delay, bandwidth, and queue size
        # https://unix.stackexchange.com/questions/100785/bucket-size-in-tbf
        bdp = calculate_bdp(delay, 0, bw, bw)
        rtt = 2 * delay
        self.config_iface('h1-eth0', False, pacing)
        self.config_iface('h2-eth0', False, pacing)
        self.config_iface('e1-eth0', True, False, delay, loss, bw, bdp, qdisc)
        self.config_iface('e1-eth1', True, False, delay, loss, bw, bdp, qdisc)
