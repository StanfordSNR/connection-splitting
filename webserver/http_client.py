import argparse
import http.client
import ssl
import sys

def run(server_ip, server_port, verbose):
    # Set up an SSL context to ignore self-signed certificate warnings
    # For testing purposes, disable certificate verification
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # Send a GET request to the server
    conn = http.client.HTTPSConnection(server_ip, server_port, context=ctx)
    conn.request('GET', '/')

    # Get the response from the server
    response = conn.getresponse()
    if verbose:
        print('Headers:', response.getheaders(), file=sys.stderr)
    raw_bytes = response.read()
    print(f'Downloaded {len(raw_bytes)} bytes ({response.status})', file=sys.stderr)

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
    args = parser.parse_args()
    run(args.server_ip, args.server_port, args.verbose)
