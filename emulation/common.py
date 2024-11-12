import sys
import os
import select
import subprocess

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

def popen(host, cmd, background=False, logger=TRACE, stdout=False, stderr=True):
    p = host.popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if background:
        logger(f'{host.name} {cmd} &')
        return p
    else:
        logger(f'{host.name} {cmd}')
        while p.poll() is None or p.stdout.peek() or p.stderr.peek():
            ready, _, _ = select.select([p.stdout, p.stderr], [], [])
            for stream in ready:
                line = stream.readline()
                if not line:
                    continue
                if stream == p.stdout and stdout:
                    print(line.decode(), end='', file=sys.stdout)
                if stream == p.stderr and stderr:
                    print(line.decode(), end='', file=sys.stderr)
        exitcode = p.wait()
        if exitcode != 0:
            print(f'{host}({cmd}) = {exitcode}', file=sys.stderr)
            exit(1)
