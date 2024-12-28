from network import *
import argparse
from time import sleep
import subprocess
import json

def runiperf3Test(network, pep, nbytes):

    print(f"Starting iperf3 server on h2 {network.h2.IP()}...")
    server = network.h2.popen('iperf3 -s')
    sleep(1)
    print(f"Starting iperf3 client on h1 {network.h1.IP()}...")
    client = network.h1.popen(f'iperf3 -c {network.h2.IP()} -n {nbytes} --json',
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    stdout, stderr = client.communicate()

    if stderr:
        print("\n*** iperf3 Client Errors ***")
        print(stderr.decode())
    print("Stopping iperf3 server on h2...")
    server.terminate()
    network.stop()
    with open('tmp.json', 'w') as f:
        f.write(stdout.decode())

def get_linux_version():
    proc = subprocess.run(['uname', '-r'], capture_output=True, text=True, check=True)
    return proc.stdout.strip()

def set_cca(cca, network):
    version = get_linux_version()
    print(f"Running on Linux: {version}")
    cmd = f'sudo sysctl -w net.ipv4.tcp_congestion_control={cca}'

    if "4.9" in version:
        print("Setting CCA on host")
        proc = subprocess.run(['sudo', 'sysctl', '-w', f'net.ipv4.tcp_congestion_control={cca}'],
                              capture_output=True, text=True, check=True)
        print(f"Set CCA: {proc.stdout.strip()}")
        return

    print("Setting CCA on Mininet nodes")
    network.h1.cmd(cmd)
    network.h2.cmd(cmd)
    cmd = 'sysctl net.ipv4.tcp_congestion_control'
    print(f"Set CCA: {network.h1.cmd(cmd).strip()}, {network.h2.cmd(cmd).strip()}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='Basic',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('--delay1', type=int, default=20, metavar='MS',
        help='1/2 RTT on near path segment')
    parser.add_argument('--delay2', type=int, default=20, metavar='MS',
        help='1/2 RTT on far path segment')
    parser.add_argument('--loss1', type=str, default='2', metavar='PERCENT',
        help='loss (in %%) on near path segment')
    parser.add_argument('--loss2', type=str, default='2', metavar='PERCENT',
        help='loss (in %%) on near path segment')
    parser.add_argument('--bw1', type=int, default=50, metavar='MBPS',
        help='link bandwidth (in Mbps) on near path segment')
    parser.add_argument('--bw2', type=int, default=50, metavar='MBPS',
        help='link bandwidth (in Mbps) on far path segment')
    parser.add_argument('--jitter1', type=int, metavar='MS',
        help='jitter on near path segment with a default delay correlation '\
            f'of {DEFAULT_DELAY_CORR}%% and a paretonormal distribution')
    parser.add_argument('--jitter2', type=int, metavar='MS',
        help='jitter on far path segment with a default delay correlation '\
            f'of {DEFAULT_DELAY_CORR}%% and a paretonormal distribution')
    parser.add_argument('--qdisc', type=str, default='red',
        choices=['red', 'fq_codel', 'noqueue'],
        help='netem queuing discipline')
    parser.add_argument('--cca',
                        choices=['cubic', 'bbr'], default='bbr',
                        help='Congestion control algorithm at endpoints')
    parser.add_argument('--pep', action='store_true', default=False,
                        help='Enable PEP')
    parser.add_argument('-n', type=str, default='62500000',
                        help='Number of bytes to transfer in the iperf3 test (see \"iperf3 -n\")')
    parser.add_argument('-o', '--outfile', type=str, default=f'iperf3_{get_linux_version()}.json',
                        help='Output file for iperf3 results')
    args = parser.parse_args()
    network = OneHopNetwork(args.delay1, args.delay2, args.loss1, args.loss2,
                            args.bw1, args.bw2, args.jitter1, args.jitter2, args.qdisc)
    network.net.start()
    set_cca(args.cca, network)
    runiperf3Test(network, args.pep, args.n)

    print(f"Writing ouput to {args.outfile}...")
    result = json.load(open('tmp.json', 'r'))
    os.system('sudo rm tmp.json')
    result = { 'parameters': vars(args), 'iperf3_result': result }
    with open(args.outfile, 'w') as f:
        json.dump(result, f, indent=4)