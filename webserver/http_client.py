import argparse
import http.client
import ssl
import sys
import time

def run(server_ip, server_port, n, verbose):
    # Set up an SSL context to ignore self-signed certificate warnings
    # For testing purposes, disable certificate verification
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # Send a GET request to the server
    start = time.monotonic()
    conn = http.client.HTTPSConnection(server_ip, server_port, context=ctx)
    conn.request('GET', f'/?n={n}')

    # Get the response from the server
    response = conn.getresponse()
    raw_bytes = response.read()
    end = time.monotonic()
    if verbose:
        print('Status:', response.status)
        print('Headers:')
        for k, v in response.getheaders():
            print(f'\t{k}: {v}')
        print('Body:', raw_bytes[:min(len(raw_bytes), 1024)])
    print(f'Downloaded {len(raw_bytes)} bytes')
    print(
        f'[TCP_CLIENT] status_code={response.status} time_s={end - start}',
        file=sys.stderr,
    )

    # Close the connection
    conn.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='HTTPS TCP client',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('--server-ip', type=str, default='127.0.0.1')
    parser.add_argument('--server-port', type=int, default=8443)
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-n', type=int, default=1000000,
        help='Number of bytes to request, 1e6 is 1 MB')
    args = parser.parse_args()
    run(args.server_ip, args.server_port, args.n, args.verbose)
