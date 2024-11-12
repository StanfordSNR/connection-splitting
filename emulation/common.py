import sys
import os

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

def popen(host, cmd):
    p = host.popen(cmd.split(' '))
    exitcode = p.wait()
    for line in p.stderr:
        sys.stderr.buffer.write(line)
    if exitcode != 0:
        print(f'{host}({cmd}) = {exitcode}')
        sys.stderr.buffer.write(b'\n')
        sys.stderr.buffer.flush()
        exit(1)
