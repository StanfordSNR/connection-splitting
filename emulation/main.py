import argparse
import sys
import time
from common import *
from network import *
from benchmark import *
from mininet.cli import CLI
from mininet.log import setLogLevel


def benchmark_http1():
    pass


def benchmark_http3(net, args):
    bm = QUICBenchmark(net)
    bm.run()


def benchmark_webrtc():
    pass


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
    # Network Configurations
    ###########################################################################
    net_config = parser.add_argument_group('net_config')
    net_config.add_argument('--delay1', type=int, default=1, metavar='MS',
        help='1/2 RTT on near path segment')
    net_config.add_argument('--delay2', type=int, default=25, metavar='MS',
        help='1/2 RTT on far path segment')
    net_config.add_argument('--loss1', type=int, default=1, metavar='PERCENT',
        help='loss (in %%) on near path segment')
    net_config.add_argument('--loss2', type=str, default='0', metavar='PERCENT',
        help='loss (in %%) on near path segment')
    net_config.add_argument('--bw1', type=int, default=100, metavar='MBPS',
        help='link bandwidth (in Mbps) on near path segment')
    net_config.add_argument('--bw2', type=int, default=10, metavar='MBPS',
        help='link bandwidth (in Mbps) on far path segment')
    net_config.add_argument('--print-statistics', action='store_true',
        help='Print statistics on number of packets sent at each host')

    ###########################################################################
    # HTTP/1.1+TCP benchmark
    ###########################################################################
    tcp = subparsers.add_parser('tcp')
    tcp.set_defaults(ty='benchmark', benchmark=benchmark_http1)

    ###########################################################################
    # HTTP/3+QUIC benchmark
    ###########################################################################
    quic = subparsers.add_parser('quic')
    quic.set_defaults(ty='benchmark', benchmark=benchmark_http3)

    ###########################################################################
    # WebRTC benchmark
    ###########################################################################
    webrtc = subparsers.add_parser('webrtc')
    webrtc.set_defaults(ty='benchmark', benchmark=benchmark_webrtc)

    ###########################################################################
    # Experiment configurations
    ###########################################################################

    args = parser.parse_args()
    net = OneHopNetwork(args.delay1, args.delay2, args.loss1, args.loss2,
        args.bw1, args.bw2)

    try:
        if args.ty == 'cli':
            CLI(net.net)
        else:
            if args.print_statistics:
                net.statistics.start()
                args.benchmark(net, args)
                net.statistics.stop_and_print()
            else:
                args.benchmark(net, args)
    finally:
        net.stop()
