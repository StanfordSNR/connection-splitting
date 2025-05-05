"""
Test network.py.
"""
import unittest
import os
import subprocess
import time
import tempfile
from mininet.node import Host
from typing import List
from network import *


class PingResult:
    def __init__(self, output):
        # Parse each individual ping
        self.pings = []
        pattern = r'bytes from ([\d\.]+): icmp_seq=(\d+)'
        for line in output.split('\n'):
            match = re.search(pattern, line)
            if match:
                ip = match.group(1)
                icmp_seq = int(match.group(2))
                self.pings.append((ip, icmp_seq))

        # Parse the result summary
        pattern = (
            r'\s+(?P<packets_tx>\d+) packets transmitted, '
            r'(?P<packets_rx>\d+) received, .*'
            r'(?P<packet_loss>[\d.]+)% packet loss, '
            r'time (?P<total_time>\d+)ms\s+'
            r'rtt min/avg/max/mdev = '
            r'(?P<rtt_min>[\d.]+)/(?P<rtt_avg>[\d.]+)/'
            r'(?P<rtt_max>[\d.]+)/(?P<rtt_mdev>[\d.]+) ms.*'
        )
        match = re.search(pattern, output)
        if match:
            self.success = True
            self.match = match.groupdict()
        else:
            self.success = False

    def packets_tx(self):
        return int(self.match['packets_tx'])

    def packets_rx(self):
        return int(self.match['packets_rx'])

    def packet_loss(self):
        """Packet loss, in %"""
        return float(self.match['packet_loss'])

    def total_time(self):
        """Total time, in ms"""
        return float(self.match['total_time'])

    def rtt_min(self):
        """Minimum RTT, in ms"""
        return float(self.match['rtt_min'])

    def rtt_avg(self):
        """Average RTT, in ms"""
        return float(self.match['rtt_avg'])

    def rtt_max(self):
        """Maximum RTT, in ms"""
        return float(self.match['rtt_max'])

    def rtt_mdev(self):
        """Mean deviation, in ms"""
        return float(self.match['rtt_mdev'])


class NetworkTestCase(unittest.TestCase):
    def setUp(self):
        # Suppress stderr logging from network setup
        self._stderr = sys.stderr
        sys.stderr = open(os.devnull, 'w')

        # Default parameters
        self.threshold = 20

        self.net = None
        self.stopped = True

    def stopNetwork(self):
        if not self.stopped:
            self.net.stop()
            self.stopped = True

    def tearDown(self):
        self.stopNetwork()

    def setUpTwoSegmentNetwork(
        self, delay1=1, delay2=10, loss1=0, loss2=0, bw1=50, bw2=10,
        qdisc='red', pacing=False, setup_time=0, cache=True,
    ) -> TwoSegmentNetwork:
        net = TwoSegmentNetwork(delay1, delay2, loss1, loss2, bw1, bw2,
                                qdisc, pacing)
        if cache:
            self.stopNetwork()
            self.net = net
            self.stopped = False
        if setup_time > 0:
            time.sleep(setup_time)
        return net

    def setUpOneSegmentNetwork(
        self, delay=10, loss=0, bw=10, qdisc='red', pacing=False,
        setup_time=0, cache=True,
    ) -> OneSegmentNetwork:
        net = OneSegmentNetwork(delay, loss, bw, qdisc, pacing)
        if cache:
            self.stopNetwork()
            self.net = net
            self.stopped = False
        if setup_time > 0:
            time.sleep(setup_time)
        return net

    def ping(self, node1, node2, n=1, interval=0.05) -> PingResult:
        """Send n pings from node1 from node2.

        Asserts that the node is reachable and at least one ping reply was
        received. Assertions may be flaky with loss, but n should be large
        enough that receiving no replies is statistically unlikely.

        Returns the parsed ping statistics.
        """
        output = node1.cmd(f'ping -i {interval} -c {n} {node2.IP()}')
        result = PingResult(output)
        debug_output = f'{node1.name} -> {node2.name}\n{output}'
        self.assertTrue(result.success, debug_output)
        self.assertEqual(result.packets_tx(), n)
        return result


class TestPopen(NetworkTestCase):
    def setUp(self):
        super().setUp()
        self.setUpOneSegmentNetwork()

    def test_invalid_configurations(self):
        logfile = tempfile.NamedTemporaryFile()
        cmd = 'true'
        with self.assertRaises(AssertionError):
            self.net.popen(None, cmd, func=lambda line: line)
        with self.assertRaises(AssertionError):
            self.net.popen(None, cmd, timeout=60)
        with self.assertRaises(AssertionError):
            self.net.popen(None, cmd, logfile=logfile.name)
        with self.assertRaises(AssertionError):
            self.net.popen(self.net.h1, cmd, background=True, timeout=60)

    def test_timeout_succeeds(self):
        """Test timeout, only on mininet hosts and synchronous processes.
        """
        host = self.net.h1
        self.assertFalse(self.net.popen(host, 'sleep 1', timeout=None))
        self.assertFalse(self.net.popen(host, 'sleep 1', timeout=2))
        self.assertTrue(self.net.popen(host, 'sleep 2', timeout=1))

    def _test_raises_exception_on_bad_exitcode(self, host):
        good_cmd = 'true'
        bad_cmd = '>'  # todo
        self.net.popen(host, good_cmd, raise_error=True)
        self.net.popen(host, good_cmd, raise_error=False) # no error to suppress
        with self.assertRaises(ValueError, msg='error raises an exception'):
            self.net.popen(host, bad_cmd, raise_error=True)
        self.net.popen(host, bad_cmd, raise_error=False)  # error is suppressed

    def test_raises_exception_on_bad_exitcode(self):
        self._test_raises_exception_on_bad_exitcode(None)
        self._test_raises_exception_on_bad_exitcode(self.net.h1)

    def _test_console_logger_logs_command(self, host, background):
        log = []
        def logger(line):
            log.append(line)

        # Run a simple command to completion
        cmd = 'true'
        self.assertEqual(len(log), 0)
        self.net.popen(host, cmd, background=background, console_logger=logger)
        self.assertEqual(len(log), 1)

        # Check the prefix and suffix of the logged command
        if host is not None:
            self.assertIn(host.name, log[0])
        if background:
            self.assertIn('&', log[0])
        else:
            self.assertNotIn('&', log[0])

    def test_console_logger_logs_command(self):
        self._test_console_logger_logs_command(None, False)
        self._test_console_logger_logs_command(self.net.h1, False)
        self._test_console_logger_logs_command(self.net.h1, True)

    def _test_console_logger_logs_stdout_and_stderr(self, host):
        log = []
        def logger(line):
            log.append(line)

        def popen(stdout, stderr):
            stdout_cmd = f'echo stdout'
            stderr_cmd = f'ls nonexistent_stderr_file_name_1234'
            self.net.popen(host, stdout_cmd, console_logger=logger,
                stdout=stdout, stderr=stderr, raise_error=False)
            self.net.popen(host, stderr_cmd, console_logger=logger,
                stdout=stdout, stderr=stderr, raise_error=False)

        def count_string(log, string):
            log = filter(lambda line: 'echo' not in line, log)
            log = filter(lambda line: 'ls ' not in line, log)
            log = filter(lambda line: string in line, log)
            return len(list(log))

        # Log neither stdout nor stderr
        popen(stdout=False, stderr=False)
        self.assertEqual(len(log), 2, log)
        self.assertEqual(count_string(log, 'stdout'), 0, log)
        self.assertEqual(count_string(log, 'stderr'), 0, log)

        # Log stdout only
        popen(stdout=True, stderr=False)
        self.assertEqual(len(log), 5, log)
        self.assertEqual(count_string(log, 'stdout'), 1, log)
        self.assertEqual(count_string(log, 'stderr'), 0, log)

        # Log stderr only
        popen(stdout=False, stderr=True)
        self.assertEqual(len(log), 8, log)
        self.assertEqual(count_string(log, 'stdout'), 1, log)
        self.assertEqual(count_string(log, 'stderr'), 1, log)

        # Log both stdout and stderr
        popen(stdout=True, stderr=True)
        self.assertEqual(len(log), 12, log)
        self.assertEqual(count_string(log, 'stdout'), 2, log)
        self.assertEqual(count_string(log, 'stderr'), 2, log)

    def test_console_logger_logs_stdout_and_stderr(self):
        self._test_console_logger_logs_stdout_and_stderr(None)
        self._test_console_logger_logs_stdout_and_stderr(self.net.h1)

    def test_stop_background_processes(self):
        host = self.net.h1
        cmd = 'sleep 60'

        def count_active_background_processes():
            processes = self.net.background_processes
            processes = filter(lambda p: p.returncode is None, processes)
            return len(list(processes))

        def count_active_background_threads():
            threads = self.net.background_threads
            threads = filter(lambda t: t.is_alive(), threads)
            return len(list(threads))

        # Start two background processes
        self.assertEqual(len(self.net.background_processes), 0)
        self.assertEqual(len(self.net.background_threads), 0)
        p1, t1 = self.net.popen(host, cmd, background=True)
        self.assertEqual(len(self.net.background_processes), 1)
        self.assertEqual(len(self.net.background_threads), 1)
        p2, t2 = self.net.popen(host, cmd, background=True)
        self.assertEqual(len(self.net.background_processes), 2)
        self.assertEqual(len(self.net.background_threads), 2)
        self.assertIsNone(p1.returncode, 'p1 is still running')
        self.assertIsNone(p2.returncode, 'p2 is still running')
        self.assertTrue(t1.is_alive(), 't1 is still alive')
        self.assertTrue(t2.is_alive(), 't2 is still alive')
        self.assertEqual(count_active_background_processes(), 2)
        self.assertEqual(count_active_background_threads(), 2)

        # Terminate one background process
        p1.terminate()
        p1.wait()
        t1.join()
        self.assertEqual(count_active_background_processes(), 1)
        self.assertEqual(count_active_background_threads(), 1)

        # Stop the entire emulation
        self.net.stop()
        self.stopped = True
        self.assertEqual(count_active_background_processes(), 0)
        self.assertEqual(count_active_background_threads(), 0)

    def _test_callback_function(self, host, background, seq=10):
        # Define the callback function. The function can interact with objects
        # passed by reference from outside the function.
        total_even = [0]
        def count_even(line):
            total_even[0] += (int(line) + 1) % 2

        # Execute the process and run to completion
        self.assertEqual(total_even[0], 0)
        cmd = f'seq {seq}'
        p = self.net.popen(host, cmd, background=background, func=count_even)
        if background:
            p[0].wait()
            p[1].join()
        self.assertEqual(total_even[0], seq // 2)

    def test_callback_function(self):
        self._test_callback_function(self.net.h1, False)
        self._test_callback_function(self.net.h1, True)

    def _test_appends_output_to_logfile(self, background: bool):
        host = self.net.h1
        logfile = tempfile.NamedTemporaryFile()

        def popen():
            stdout_cmd = f'echo stdout'
            stderr_cmd = f'ls nonexistent_stderr_file_name_1234'
            p1 = self.net.popen(host, stdout_cmd, background=background,
                    logfile=logfile.name, raise_error=False)
            p2 = self.net.popen(host, stderr_cmd, background=background,
                    logfile=logfile.name, raise_error=False)
            if background:
                p1[0].wait()
                p2[0].wait()
                p1[1].join()
                p2[1].join()

        def count_string(log, string):
            log = filter(lambda line: string in line, log)
            return len(list(log))

        # Contents from both stdout and stderr should be written to the logfile
        popen()
        with open(logfile.name, 'r') as f:
            contents_after_one_run = f.readlines()
        self.assertEqual(count_string(contents_after_one_run, 'stdout'), 1,
            contents_after_one_run)
        self.assertEqual(count_string(contents_after_one_run, 'stderr'), 1,
            contents_after_one_run)

        # Contents should be appended to the logfile on the second run
        popen()
        with open(logfile.name, 'r') as f:
            contents_after_two_runs = f.readlines()
        self.assertEqual(count_string(contents_after_two_runs, 'stdout'), 2,
            contents_after_two_runs)
        self.assertEqual(count_string(contents_after_two_runs, 'stderr'), 2,
            contents_after_two_runs)

    def test_appends_output_to_logfile(self):
        self._test_appends_output_to_logfile(background=False)
        self._test_appends_output_to_logfile(background=True)


class TestPrepopulateArpTable(NetworkTestCase):
    def setUp(self):
        super().setUp()
        self.cwd = os.getcwd()
        os.chdir('..') # run from base directory
        self._logdir = tempfile.TemporaryDirectory()
        self.logdir = self._logdir.name
        self.logfile = f'{self._logdir.name}/{ROUTER_LOGFILE}'

    def tearDown(self):
        super().tearDown()
        self._logdir.cleanup()
        os.chdir(self.cwd)

    def ping_all(self, hosts: List[Host]):
        for h1 in hosts:
            for h2 in hosts:
                if h1 != h2:
                    self.ping(h1, h2, 1)

    def check_pcap(self, iface, lines, num_pings):
        icmp = 0
        arps = []
        for line in lines:
            if 'ICMP echo reply' in line:
                icmp += 1
            elif 'ARP' in line:
                arps.append(line)
        self.assertEqual(len(arps), 0, f'{iface}\n' + '\n'.join(arps))
        self.assertGreater(icmp, 0, 'tcpdump did not capture the ping, may need to sleep longer')

    def check_arp_table_is_used(
        self, net: TwoSegmentNetwork, hosts: List[Host], ping_tunnel: bool=False,
    ):
        # for host in hosts: print('BEFORE:', host.name, host.cmd('ip neigh show'))
        if ping_tunnel:
            for (host1, host2) in [
                (net.h1, net.h2),
                (net.h1, net.p0),
                (net.p0, net.p1),
                (net.p1, net.h2),
            ]:
                self.ping(host1, host2, 1)
                self.ping(host2, host1, 1)
        else:
            self.ping_all(hosts)
        time.sleep(1)
        # for host in hosts: print('AFTER:', host.name, host.cmd('ip neigh show'))
        self.stopNetwork()
        for iface in net.primary_ifaces:
            filename = f'{self.logdir}/{iface}.pcap'
            self.assertTrue(os.path.exists(filename))
            p = subprocess.run(f'tcpdump -r {filename}', shell=True,
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            lines = p.stdout.split('\n')
            self.check_pcap(iface, lines, len(hosts) - 1)

    def test_arp_one_segment_network(self):
        net = self.setUpOneSegmentNetwork()
        net.start_tcpdump(logdir=self.logdir)
        time.sleep(1)
        self.check_arp_table_is_used(net, [net.h1, net.h2])

    def test_arp_two_segment_network(self):
        net = self.setUpTwoSegmentNetwork()
        net.start_tcpdump(logdir=self.logdir)
        time.sleep(1)
        self.check_arp_table_is_used(net, [net.h1, net.h2])
