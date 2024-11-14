import os
import select
import sys

SERVER_LOGFILE = 'server.log'
CLIENT_LOGFILE = 'client.log'

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
    print(f'[SIDEKICK:{level}] {val}', file=sys.stderr);

def init_logdir(path):
    os.system(f'mkdir -p {path}')
    with open(f'{path}/{SERVER_LOGFILE}', 'w') as _:
        pass
    with open(f'{path}/{CLIENT_LOGFILE}', 'w') as _:
        pass

def read_subprocess_pipe(p):
    while p.poll() is None or p.stdout.peek() or p.stderr.peek():
        ready, _, _ = select.select([p.stdout, p.stderr], [], [])
        for stream in ready:
            line = stream.readline()
            if not line:
                continue
            yield (line.decode(), stream)

def handle_background_process(p, logfile, func):
    for line, stream in read_subprocess_pipe(p):
        if logfile is not None:
            with open(logfile, 'a') as f:
                f.write(line)
        if func is not None:
            func(line)
