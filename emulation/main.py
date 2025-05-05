import argparse
import sys
import time
from common import *
from network import *
from benchmark import *
from mininet.cli import CLI
from mininet.log import setLogLevel


def benchmark_tcp(net, args):
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


def benchmark_google(net, args):
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

def benchmark_cloudflare(net, args):
    bm = CloudflareQUICBenchmark(
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

def benchmark_picoquic(net, args):
    bm = PicoQUICBenchmark(
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
    exp_config.add_argument('--logdir', type=str, default='/tmp/atc25-logs',
        help='Directory where host logs are written, in server.log and client.log')
    exp_config.add_argument('--network-statistics', action='store_true',
        help='Include measured network statistics in experiment output')
    exp_config.add_argument('--topology',
        choices=['one_hop', 'direct'], default='one_hop',
        help='Network topology to use. If "direct", uses the network path '\
             'properties for the "near path segment" i.e. Link 1.')
    exp_config.add_argument('--pep', action='store_true',
        help='Enable PEPsal, a connection-splitting TCP PEP')

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
    net_config.add_argument('--qdisc', type=str, default='red',
        choices=['red', 'bfifo-large', 'bfifo-small', 'pie', 'codel',
                 'policer', 'fq_codel'],
        help='netem queuing discipline')

    ###########################################################################
    # HTTP/1.1+TCP benchmark
    ###########################################################################
    tcp = subparsers.add_parser(
        'tcp',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    tcp.set_defaults(ty='benchmark', benchmark=benchmark_tcp)
    tcp.add_argument('-n', type=parse_data_size, default=1000000,
        help='Number of bytes to download in the HTTP/1.1 GET request, '\
             'e.g., 1000, 1K, 1M, 1000000, 1G')
    tcp.add_argument('-cca', '--congestion-control',
        choices=['reno', 'cubic', 'bbr', 'bbr2'], default='cubic',
        help='Congestion control algorithm at endpoints')
    tcp.add_argument('--certfile', type=str, default=DEFAULT_SSL_CERTFILE,
        help='Path to SSL certificate')
    tcp.add_argument('--keyfile', type=str, default=DEFAULT_SSL_KEYFILE,
        help='Path to SSL key')

    ###########################################################################
    # HTTP/3+QUIC benchmark
    ###########################################################################
    google = subparsers.add_parser(
        'google',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    google.set_defaults(ty='benchmark', benchmark=benchmark_google)
    google.add_argument('-n', type=parse_data_size, default=1000000,
        help='Number of bytes to download in the HTTP/3 GET request, '\
             'e.g., 1000, 1K, 1M, 1000000, 1G')
    google.add_argument('-cca', '--congestion-control',
        choices=['cubic', 'reno', 'bbr1', 'bbr'], default='cubic',
        help='Congestion control algorithm at endpoints')
    google.add_argument('--certfile', type=str, default=DEFAULT_SSL_CERTFILE,
        help='Path to SSL certificate')
    google.add_argument('--keyfile', type=str, default=DEFAULT_SSL_KEYFILE_GOOGLE,
        help='Path to SSL key')

    ###########################################################################
    # HTTP/3+Cloudflare QUIC benchmark
    ###########################################################################
    cloudflare = subparsers.add_parser(
        'cloudflare',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    cloudflare.set_defaults(ty='benchmark', benchmark=benchmark_cloudflare)
    cloudflare.add_argument('-n', type=parse_data_size, default=1000000,
        help='Number of bytes to download in the HTTP/3 GET request, '\
             'e.g., 1000, 1K, 1M, 1000000, 1G')
    cloudflare.add_argument('-cca', '--congestion-control',
        choices=['cubic', 'reno', 'bbr2', 'bbr'], default='cubic',
        help='Congestion control algorithm at endpoints')
    cloudflare.add_argument('--certfile', type=str, default=DEFAULT_SSL_CERTFILE,
        help='Path to SSL certificate')
    cloudflare.add_argument('--keyfile', type=str, default=DEFAULT_SSL_KEYFILE,
        help='Path to SSL key')

    ###########################################################################
    # HTTP/3+picoquic QUIC benchmark
    ###########################################################################
    picoquic = subparsers.add_parser(
        'picoquic',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    picoquic.set_defaults(ty='benchmark', benchmark=benchmark_picoquic)
    picoquic.add_argument('-n', type=parse_data_size, default=1000000,
        help='Number of bytes to download in the HTTP/3 GET request, '\
             'e.g., 1000, 1K, 1M, 1000000, 1G')
    picoquic.add_argument('-cca', '--congestion-control',
        choices=['newreno', 'cubic', 'dcubic', 'fast', 'bbr', 'prague', 'bbr1'], default='cubic',
        help='Congestion control algorithm at endpoints')
    picoquic.add_argument('--certfile', type=str, default=DEFAULT_SSL_CERTFILE,
        help='Path to SSL certificate')
    picoquic.add_argument('--keyfile', type=str, default=DEFAULT_SSL_KEYFILE,
        help='Path to SSL key')

    args = parser.parse_args()

    # Some BBR implementations require pacing.
    # This includes Cloudflare quiche and Linux kernel versions <5.0.
    # We automatically set pacing for Linux TCP BBR, but we need to set it
    # here for user-space implementations.
    if args.benchmark == benchmark_cloudflare and 'bbr' in args.congestion_control:
        pacing = True
    else:
        pacing = False

    if args.topology == 'one_hop':
        net = TwoSegmentNetwork(args.delay1, args.delay2,
            args.loss1, args.loss2, args.bw1, args.bw2, args.qdisc, pacing)
        if args.pep:
            net.start_tcp_pep(logdir=args.logdir)
    elif args.topology == 'direct':
        assert not args.pep
        net = OneSegmentNetwork(args.delay1, args.loss1, args.bw1,
            args.qdisc, pacing)
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
