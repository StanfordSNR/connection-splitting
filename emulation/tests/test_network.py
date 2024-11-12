import unittest
from network import *


class TestNetStatistics(unittest.TestCase):
    def setUp(self):
        pass

    def test_tx_and_rx_statistics(self):
        pass


class TestOneHopNetwork(unittest.TestCase):
    def setUp(self):
        pass

    def test_ip(self):
        self.assertEqual(OneHopNetwork._ip(1), '10.0.1.10/24')
        self.assertEqual(OneHopNetwork._ip(2), '10.0.2.10/24')
        self.assertEqual(OneHopNetwork._ip(0), '10.0.0.10/24')
        self.assertEqual(OneHopNetwork._ip(9), '10.0.9.10/24')
        with self.assertRaises(AssertionError):
            OneHopNetwork._ip(10)
        with self.assertRaises(AssertionError):
            OneHopNetwork._ip(-1)

    def test_mac(self):
        self.assertEqual(OneHopNetwork._mac(1), '00:00:00:00:00:01')
        self.assertEqual(OneHopNetwork._mac(2), '00:00:00:00:00:02')
        self.assertEqual(OneHopNetwork._mac(0), '00:00:00:00:00:00')
        self.assertEqual(OneHopNetwork._mac(9), '00:00:00:00:00:09')
        with self.assertRaises(AssertionError):
            OneHopNetwork._mac(10)
        with self.assertRaises(AssertionError):
            OneHopNetwork._mac(-1)

    def test_calculate_bdp(self):
        pass

    def test_hosts_exist_and_are_reachable(self):
        pass

    def test_delay_config(self):
        pass

    def test_bandwidth_config(self):
        pass

    def test_loss_config(self):
        pass

    def test_queue_size_config(self):
        pass


class SidekickNetwork(unittest.TestCase):
    def setUp(self):
        pass
