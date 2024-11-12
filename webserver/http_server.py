import argparse
import http.server
import ssl
import sys
import os

DEFAULT_CERTFILE = f'{os.environ["HOME"]}/sidekick-downloads/deps/chromium/'\
                    'src/net/tools/quic/certs/out/leaf_cert.pem',
DEFAULT_KEYFILE  = f'{os.environ["HOME"]}/sidekick-downloads/deps/chromium/'\
                    'src/net/tools/quic/certs/out/leaf_cert.key',

# Set up a basic request handler
class SimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Send a 200 OK response
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        # Send a simple HTML response
        self.wfile.write(b'<html><body><h1>Hello, HTTPS World!</h1></body></html>')

# Set up the HTTPS server
def run(server_ip, server_port, certfile, keyfile):
    server_address = (server_ip, server_port)
    httpd = http.server.HTTPServer(server_address, SimpleHTTPRequestHandler)

    # Wrap the socket with SSL
    httpd.socket = ssl.wrap_socket(
        httpd.socket,
        server_side=True,
        certfile=certfile,
        keyfile=keyfile,
        ssl_version=ssl.PROTOCOL_TLS,
    )

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
    args = parser.parse_args()
    run(args.server_ip, args.server_port, args.certfile, args.keyfile)
