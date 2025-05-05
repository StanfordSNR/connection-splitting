import os
import select
import sys
import subprocess
import re
from enum import Enum

SERVER_LOGFILE = 'server.log'
CLIENT_LOGFILE = 'client.log'
ROUTER_LOGFILE = 'router.log'

DEFAULT_SSL_CERTFILE = f'deps/certs/out/leaf_cert.pem'
DEFAULT_SSL_KEYFILE = f'deps/certs/out/leaf_cert.key'
DEFAULT_SSL_KEYFILE_GOOGLE = f'deps/certs/out/leaf_cert.pkcs8'

SETUP_TIMEOUT = 10
LINUX_TIMEOUT_EXITCODE = 124
HTTP_OK_STATUSCODE = 200
HTTP_TIMEOUT_STATUSCODE = 408

# Log a benchmark result every this number of seconds so there is console
# output, even if there are still trials remaining.
LOG_CHUNK_TIME = 300

DEFAULT_DELAY_CORR = 40

class Protocol(Enum):
    LINUX_TCP = 0
    GOOGLE_QUIC = 1
    CLOUDFLARE_QUIC = 2
    PICOQUIC = 3

def TRACE(val):
    # LOG(val, 'TRACE')
    pass

def DEBUG(val):
    LOG(val, 'DEBUG')

def INFO(val):
    LOG(val, 'INFO')

def WARN(val):
    LOG(val, 'WARN')

def ERROR(val):
    LOG(val, 'ERROR')

def LOG(val, level):
    print(f'[{level}] {val}', file=sys.stderr);

def mac(digit):
    assert 0 <= digit < 10
    return f'00:00:00:00:00:0{int(digit)}'

def calculate_bdp(delay1, delay2, bw1, bw2):
    rtt_ms = 2 * (delay1 + delay2)
    bw_mbps = min(bw1, bw2)
    return rtt_ms * bw_mbps * 1000000. / 1000. / 8.

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

def init_logdir(path):
    os.system(f'mkdir -p {path}')
    os.system(f'rm -f {path}/*')

def read_subprocess_pipe(p):
    streams = [p.stdout, p.stderr]
    while p.poll() is None:
        ready, _, _ = select.select(streams, [], [])
        for stream in ready:
            while True:
                line = stream.readline()
                if not line:
                    break
                yield (line, stream)
    for stream in streams:
        for line in stream.readlines():
            yield (line, stream)
    stdout, stderr = p.communicate()
    for line in stdout.splitlines(keepends=True):
        yield (line, p.stdout)
    for line in stderr.splitlines(keepends=True):
        yield (line, p.stderr)

def handle_background_process(p, logfile, func):
    # Only call the callback function
    if logfile is None:
        for line, _ in read_subprocess_pipe(p):
            if func is not None:
                func(line)
        return

    # Both write to the logfile and call the callback function
    for line, _ in read_subprocess_pipe(p):
        if func is not None:
            func(line)
        with open(logfile, 'a') as f:
            f.write(line)

def get_linux_version():
    proc = subprocess.run(['uname', '-r'], capture_output=True, text=True, check=True)
    version = proc.stdout.strip()
    return float(re.search(r'^\d+\.\d+', version).group())
