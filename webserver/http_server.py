import argparse
import http.server
import ssl
import sys
import os
from urllib.parse import urlparse, parse_qs

DEFAULT_CERTFILE = f'{os.environ["HOME"]}/sidekick-downloads/deps/certs/out/leaf_cert.pem'
DEFAULT_KEYFILE  = f'{os.environ["HOME"]}/sidekick-downloads/deps/certs/out/leaf_cert.key'
CACHE = b''

# Set up a basic request handler
class SimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        global CACHE
        # Parse query param to determine number of bytes to send
        path = urlparse(self.path)
        try:
            params = parse_qs(path.query)
            n = int(params['n'][0])
            assert n > 0
        except Exception as e:
            print(e, file=sys.stderr)
            # Send a 400 Bad Request response
            self.send_response(400)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Invalid request. Use GET /?n=<positive int>')
            return

        if n > len(CACHE):
            # Send a 400 Bad Request response
            self.send_response(400)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(f'Invalid request. {len(CACHE)} < {n} bytes in cache'.encode('utf-8'))
        else:
            # Send a 200 OK response
            self.send_response(200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Length', str(n))
            self.end_headers()
            self.wfile.write(CACHE[:n])

# Initialize the response data cache
def init_cache(n):
    global CACHE
    CACHE = os.urandom(n)

# Set up the HTTPS server
def run(server_ip, server_port, certfile, keyfile):
    server_address = (server_ip, server_port)
    httpd = http.server.HTTPServer(server_address, SimpleHTTPRequestHandler)

    # Wrap the socket with SSL
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certfile=certfile, keyfile=keyfile)
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)

    print(f'Serving on https://{server_ip}:{server_port}', file=sys.stderr)
    httpd.serve_forever()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='HTTPS TCP server',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('--server-ip', type=str, default='127.0.0.1')
    parser.add_argument('--server-port', type=int, default=8443)
    parser.add_argument('--certfile', type=str, default=DEFAULT_CERTFILE)
    parser.add_argument('--keyfile', type=str, default=DEFAULT_KEYFILE)
    parser.add_argument('-n', type=int, default=1000000,
        help='Number of random bytes to initialize in the cache, 1e6 is 1 MB')
    parser.add_argument('--chunk-size', type=int, required=False)
    args = parser.parse_args()

    init_cache(args.n)
    run(args.server_ip, args.server_port, args.certfile, args.keyfile)
