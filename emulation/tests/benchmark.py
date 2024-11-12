"""
A one hop network with code executing on the endpoints and middlebox.
"""
class SidekickNetwork(OneHopNetwork):
    def __init__(self, delay1, delay2, loss1, loss2, bw1, bw2):
        super().__init__(delay1, delay2, loss1, loss2, bw1, bw2)
        self.background_processes = []

    def stop(self):
        for p in self.background_processes:
            p.terminate()
            p.wait()
        if self.net is not None:
            self.net.stop()

    ###########################################################################
    # SERVER
    ###########################################################################

    def start_http1_tcp_webserver(self):
        pass

    def start_http3_quic_webserver(self):
        base = 'deps/chromium/src'
        cmd = f'./{base}/out/Default/quic_server '\
        f'--quic_response_cache_dir=/tmp/quic-data/www.example.org '\
        f'--certificate_file={base}/net/tools/quic/certs/out/leaf_cert.pem '\
        f'--key_file={base}/net/tools/quic/certs/out/leaf_cert.pkcs8'
        p = popen(self.h2, cmd, background=True, logger=DEBUG)
        self.background_processes.append(p)

    def start_webrtc_sender(self):
        pass

    ###########################################################################
    # CLIENT
    ###########################################################################

    def run_http1_tcp_client(self):
        pass

    def run_http3_quic_client(self):
        base = 'deps/chromium/src'
        cmd = f'./{base}/out/Default/quic_client --allow_unknown_root_cert '\
        f'--host={self.h2.IP()} --port=6121 https://www.example.org/'
        popen(self.h1, cmd, background=False, logger=DEBUG, stdout=True)

    def start_webrtc_receiver(self):
        pass

    ###########################################################################
    # MIDDLEBOX
    ###########################################################################

    def start_tcp_pep(self):
        DEBUG('Starting the TCP PEP on r1...')
        popen(self.r1, 'ip rule add fwmark 1 lookup 100')
        popen(self.r1, 'ip route add local 0.0.0.0/0 dev lo table 100')
        popen(self.r1, 'iptables -t mangle -F')
        popen(self.r1, 'iptables -t mangle -A PREROUTING -i r1-eth1 -p tcp -j TPROXY --on-port 5000 --tproxy-mark 1')
        popen(self.r1, 'iptables -t mangle -A PREROUTING -i r1-eth0 -p tcp -j TPROXY --on-port 5000 --tproxy-mark 1')
        self.r1.cmd('pepsal -v >> r1.log 2>&1 &')

    def start_sidekick(self):
        pass
