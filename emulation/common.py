import sys
import os


def DEBUG(val):
    LOG(val)

def INFO(val):
    LOG(val)

def WARN(val):
    LOG(val)

def ERROR(val):
    LOG(val)

def LOG(val):
    print(f'[sidekick] {val}', file=sys.stderr);

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
