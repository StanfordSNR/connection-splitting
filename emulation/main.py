import argparse
import sys
import time
from common import *
from network import *
from benchmark import *
from mininet.cli import CLI
from mininet.log import setLogLevel


DEFAULT_SSL_CERTFILE = f'deps/certs/out/leaf_cert.pem'
DEFAULT_SSL_KEYFILE_QUIC = f'deps/certs/out/leaf_cert.pkcs8'
DEFAULT_SSL_KEYFILE_TCP = f'deps/certs/out/leaf_cert.key'


def benchmark_http1(net, args):
    assert not (args.topology == 'direct' and args.pep)
    bm = TCPBenchmark(
        net,
        args.n,
        cca=args.congestion_control,
        pep=args.pep,
        certfile=args.certfile,
        keyfile=args.keyfile,
    )
    bm.run(
        args.label,
        args.logdir,
        args.trials,
        args.timeout,
        args.network_statistics,
    )


def benchmark_http3(net, args):
    bm = QUICBenchmark(
        net,
        args.n,
        cca=args.congestion_control,
        certfile=args.certfile,
        keyfile=args.keyfile,
    )
    bm.run(
        args.label,
        args.logdir,
        args.trials,
        args.timeout,
        args.network_statistics,
    )


def benchmark_webrtc():
    pass


def parse_data_size(n):
    try:
        multiplier = 1
        if 'K' in n:
            multiplier = 1000
        elif 'M' in n:
            multiplier = 1000000
        elif 'G' in n:
            multiplier = 1000000000
        else:
            return int(n)
        return multiplier * int(n[:-1])
    except Exception:
        raise ValueError(f'invalid data size {n}')

if __name__ == '__main__':
    setLogLevel('info')

    parser = argparse.ArgumentParser(
        prog='Sidekick',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(required=True)
    cli = subparsers.add_parser('cli')
    cli.set_defaults(ty='cli')

    ###########################################################################
    # Experiment configurations
    ###########################################################################
    exp_config = parser.add_argument_group('exp_config')
    exp_config.add_argument('-t', '--trials', type=int, default=1,
        help='Number of trials')
    exp_config.add_argument('--timeout', type=int,
        help='Experiment timeout, in seconds')
    exp_config.add_argument('--label', type=str, default='NO_LABEL')
    exp_config.add_argument('--logdir', type=str, default='/tmp/sidekick-logs',
        help='Directory where host logs are written, in server.log and client.log')
    exp_config.add_argument('--network-statistics', action='store_true',
        help='Include measured network statistics in experiment output')
    exp_config.add_argument('--topology',
        choices=['one_hop', 'direct'], default='one_hop',
        help='Network topology to use. If "direct", uses the network path '\
             'properties for the "near path segment" i.e. Link 1.')

    ###########################################################################
    # Network Configurations
    ###########################################################################
    net_config = parser.add_argument_group('net_config')
    net_config.add_argument('--delay1', type=int, default=1, metavar='MS',
        help='1/2 RTT on near path segment')
    net_config.add_argument('--delay2', type=int, default=25, metavar='MS',
        help='1/2 RTT on far path segment')
    net_config.add_argument('--loss1', type=str, default='1', metavar='PERCENT',
        help='loss (in %%) on near path segment')
    net_config.add_argument('--loss2', type=str, default='0', metavar='PERCENT',
        help='loss (in %%) on near path segment')
    net_config.add_argument('--bw1', type=int, default=100, metavar='MBPS',
        help='link bandwidth (in Mbps) on near path segment')
    net_config.add_argument('--bw2', type=int, default=10, metavar='MBPS',
        help='link bandwidth (in Mbps) on far path segment')
    net_config.add_argument('--jitter1', type=int, metavar='MS',
        help='jitter on near path segment with a default delay correlation '\
            f'of {DEFAULT_DELAY_CORR}%% and a paretonormal distribution')
    net_config.add_argument('--jitter2', type=int, metavar='MS',
        help='jitter on far path segment with a default delay correlation '\
            f'of {DEFAULT_DELAY_CORR}%% and a paretonormal distribution')

    ###########################################################################
    # HTTP/1.1+TCP benchmark
    ###########################################################################
    tcp = subparsers.add_parser(
        'tcp',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    tcp.set_defaults(ty='benchmark', benchmark=benchmark_http1)
    tcp.add_argument('-n', type=parse_data_size, default=1000000,
        help='Number of bytes to download in the HTTP/1.1 GET request, '\
             'e.g., 1000, 1K, 1M, 1000000, 1G')
    tcp.add_argument('-cca', '--congestion-control',
        choices=['cubic', 'bbr'], default='cubic',
        help='Congestion control algorithm at endpoints')
    tcp.add_argument('--pep', action='store_true',
        help='Enable PEPsal, a connection-splitting TCP PEP')
    tcp.add_argument('--certfile', type=str, default=DEFAULT_SSL_CERTFILE,
        help='Path to SSL certificate')
    tcp.add_argument('--keyfile', type=str, default=DEFAULT_SSL_KEYFILE_TCP,
        help='Path to SSL key')

    ###########################################################################
    # HTTP/3+QUIC benchmark
    ###########################################################################
    quic = subparsers.add_parser(
        'quic',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    quic.set_defaults(ty='benchmark', benchmark=benchmark_http3)
    quic.add_argument('-n', type=parse_data_size, default=1000000,
        help='Number of bytes to download in the HTTP/3 GET request, '\
             'e.g., 1000, 1K, 1M, 1000000, 1G')
    quic.add_argument('-cca', '--congestion-control',
        choices=['cubic', 'reno', 'bbr1', 'bbr'], default='cubic',
        help='Congestion control algorithm at endpoints')
    quic.add_argument('--certfile', type=str, default=DEFAULT_SSL_CERTFILE,
        help='Path to SSL certificate')
    quic.add_argument('--keyfile', type=str, default=DEFAULT_SSL_KEYFILE_QUIC,
        help='Path to SSL key')

    ###########################################################################
    # WebRTC benchmark
    ###########################################################################
    webrtc = subparsers.add_parser(
        'webrtc',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    webrtc.set_defaults(ty='benchmark', benchmark=benchmark_webrtc)

    args = parser.parse_args()
    if args.topology == 'one_hop':
        net = OneHopNetwork(args.delay1, args.delay2, args.loss1, args.loss2,
            args.bw1, args.bw2, args.jitter1, args.jitter2)
    elif args.topology == 'direct':
        net = DirectNetwork(args.delay1, args.loss1, args.bw1, args.jitter1)
    else:
        raise NotImplementedError(args.topology)

    try:
        if args.ty == 'cli':
            CLI(net.net)
        else:
            init_logdir(args.logdir)
            args.benchmark(net, args)
    finally:
        net.stop()
