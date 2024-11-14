import time

from common import *


class BaseBenchmark:
    def __init__(self, net):
        self.net = net

    def start_sidekick(self):
        pass


class QUICBenchmark(BaseBenchmark):
    def __init__(self, net, n: str, certfile=None, keyfile=None):
        super().__init__(net)
        self.certfile = certfile
        self.keyfile = keyfile

        # Create cache dir
        self.cache_dir = '/tmp/quic-data/www.example.org'
        filename = f'{self.cache_dir}/index.html'
        net.popen(None, f'mkdir -p {self.cache_dir}', logger=DEBUG)
        # net.popen(None, f'head -c {n} /dev/urandom > {filename}', logger=DEBUG)

    def start_server(self):
        base = 'deps/chromium/src'
        cmd = f'./{base}/out/Default/quic_server '\
        f'--quic_response_cache_dir=/tmp/quic-data/www.example.org '\
        f'--certificate_file={self.certfile} '\
        f'--key_file={self.keyfile}'
        self.net.popen(self.net.h2, cmd, background=True, logger=DEBUG)

    def run_client(self):
        base = 'deps/chromium/src'
        cmd = f'./{base}/out/Default/quic_client --allow_unknown_root_cert '\
        f'--host={self.net.h2.IP()} --port=6121 https://www.example.org/'
        self.net.popen(self.net.h1, cmd, background=False, logger=DEBUG)

    def run(self):
        self.start_server()
        start = time.monotonic()
        self.run_client()
        end = time.monotonic()
        print(f'{end - start:.3f}')


class TCPBenchmark(BaseBenchmark):
    def __init__(self, net, certfile=None, keyfile=None):
        super().__init__(net)
        self.certfile = certfile
        self.keyfile = keyfile

    def start_server(self):
        pass

    def run_client(self):
        pass

    def start_tcp_pep(self):
        DEBUG('Starting the TCP PEP on r1...')
        popen(self.net.r1, 'ip rule add fwmark 1 lookup 100')
        popen(self.net.r1, 'ip route add local 0.0.0.0/0 dev lo table 100')
        popen(self.net.r1, 'iptables -t mangle -F')
        popen(self.net.r1, 'iptables -t mangle -A PREROUTING -i r1-eth1 -p tcp -j TPROXY --on-port 5000 --tproxy-mark 1')
        popen(self.net.r1, 'iptables -t mangle -A PREROUTING -i r1-eth0 -p tcp -j TPROXY --on-port 5000 --tproxy-mark 1')
        self.net.r1.cmd('pepsal -v >> r1.log 2>&1 &')


class WebRTCBenchmark(BaseBenchmark):
    def __init__(self, net):
        super().__init__(net)

    def start_webrtc_sender(self):
        pass

    def start_webrtc_receiver(self):
        pass
