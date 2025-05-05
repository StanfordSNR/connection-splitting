"""
Test the CLI entrypoint into the program in main.py.
"""
import unittest
import subprocess
import os
import json
import tempfile

from typing import List, Tuple

from common import *


class CLITestCase(unittest.TestCase):
    def setUp(self):
        # Run tests from the upper-level directory (the base repo)
        self._cwd = os.getcwd()
        os.chdir('..')

        # Set up logging directory
        self._logdir = tempfile.TemporaryDirectory()
        self.logdir = self._logdir.name

    def tearDown(self):
        self._logdir.cleanup()
        os.chdir(self._cwd)

    def parse_json_lines(self, output):
        lines = []
        for line in output.split('\n'):
            try:
                line = json.loads(line)
                lines.append(line)
            except json.decoder.JSONDecodeError:
                continue
        return lines

    def execute_command(
        self,
        protocol,
        network_options: List[str]=[],
        protocol_options: List[str]=[],
    ) -> Tuple[str, str]:
        cmd = ['python3', 'emulation/main.py']
        cmd += ['--logdir', self.logdir]
        cmd += network_options
        cmd += [protocol]
        cmd += protocol_options
        # print(' '.join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout, result.stderr

    def execute_command_and_check(
        self,
        protocol,
        network_options: List[str]=[],
        protocol_options: List[str]=[],
    ):
        stdout, stderr = self.execute_command(
            protocol, network_options, protocol_options)
        self.assertNotEqual(stdout, '', 'results are logged to stdout')
        lines = self.parse_json_lines(stdout)
        self.assertEqual(len(lines), 1)
        line = lines[0]
        self.assertIn('inputs', line)
        self.assertIn('outputs', line)
        outputs = line['outputs']
        self.assertEqual(len(outputs), 1)
        self.assertTrue(outputs[0].get('success'), outputs[0])
        return outputs


class TestBenchmarkCUBIC(CLITestCase):
    def test_linux_tcp_benchmark(self):
        self.execute_command_and_check('tcp', [], ['-cca', 'cubic'])

    def test_linux_tcp_benchmark_with_pep(self):
        self.execute_command_and_check('tcp', ['--pep'], ['-cca', 'cubic'])

    def test_google_quic_benchmark(self):
        self.execute_command_and_check('google', [], ['-cca', 'cubic'])

    def test_cloudflare_quic_benchmark(self):
        self.execute_command_and_check('cloudflare', [], ['-cca', 'cubic'])

    def test_picoquic_quic_benchmark(self):
        self.execute_command_and_check('picoquic', [], ['-cca', 'cubic'])


class TestBenchmarkBBR(CLITestCase):
    def test_linux_tcp_benchmark(self):
        self.execute_command_and_check('tcp', [], ['-cca', 'bbr'])

    def test_linux_tcp_benchmark_with_pep(self):
        self.execute_command_and_check('tcp', ['--pep'], ['-cca', 'bbr'])

    def test_google_quic_benchmark(self):
        self.execute_command_and_check('google', [], ['-cca', 'bbr'])

    def test_cloudflare_quic_benchmark(self):
        self.execute_command_and_check('cloudflare', [], ['-cca', 'bbr'])

    def test_picoquic_quic_benchmark(self):
        self.execute_command_and_check('picoquic', [], ['-cca', 'bbr'])
