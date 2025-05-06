"""
Test common.py.
"""
import unittest
import subprocess
from common import *


class TestSubprocessHandling(unittest.TestCase):
    def test_reads_all_subprocess_output(self):
        n = 10
        cmd = ['seq', str(n)]
        p = subprocess.Popen(cmd, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        output = []
        for line, _ in read_subprocess_pipe(p):
            output.append(line.strip())
        self.assertEqual(len(output), n, output)
        self.assertEqual(p.wait(), 0)


class TestHelperFunctions(unittest.TestCase):
    def test_calculate_bdp(self):
        delay1 = 20 # ms
        delay2 = 10
        bw1 = 10 # Mbit/s
        bw2 = 1000
        expected_mbits = 0.6 # 60ms * 10Mbit/s
        expected_bytes = expected_mbits * 1000000 / 8
        actual_bytes = calculate_bdp(delay1, delay2, bw1, bw2)
        self.assertEqual(actual_bytes, expected_bytes,
                         'calculated bdp in bytes')

    def test_mac(self):
        self.assertEqual(mac(0), '00:00:00:00:00:00')
        self.assertEqual(mac(1), '00:00:00:00:00:01')
        self.assertEqual(mac(2), '00:00:00:00:00:02')
        with self.assertRaises(AssertionError):
            mac(9999999999999)
