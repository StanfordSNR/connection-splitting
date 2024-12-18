import paramiko
import time
import sys
import logging

# Open
# Execute command
# Print output

class SSH:
    def __init__(self, ip, user="ubuntu", verbose=False):
        self.ip = ip
        self.user = user
        self.client = None
        self.wdir = None
        if verbose:
            logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

    def connect(self, debug_log=False):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(hostname=self.ip, username=self.user, timeout=15)
        print(f"Successfully connected to {self.user}@{self.ip}")

    def set_wdir(self, wdir):
        '''
        Set working directory where future commands will be executed
        (until clear_wdir is called). (Note there may be a cleaner way
        to do this with interactive shells?)
        '''
        self.wdir = wdir

    def run(self, cmd, raise_err=True, return_stdout=False):
        try:
            print(f"EXEC: {cmd}")
            cmd = f"cd {self.wdir} && {cmd}" if self.wdir else cmd
            _, stdout, _ = self.client.exec_command(cmd)
            stdout.channel.set_combine_stderr(True)
            lines = []
            while not stdout.channel.exit_status_ready():
                # Note ChannelFile built on base class BufferedFile
                l = stdout.readline()
                if return_stdout:
                    lines.append(l)
                else:
                    print(l, end="")
            exit_code = stdout.channel.recv_exit_status()
            if raise_err and exit_code != 0:
                raise Exception(f"SSH exec on {self.ip}, {cmd} return exit code {exit_code}")
            return exit_code, "\n".join(lines)

        except paramiko.SSHException as e:
            raise Exception(f"SSH exec failed for {self.ip}, {cmd} with error: {e}")

    def run_with_prompts(self, cmd, resp="\n"):
        cmd = f"cd {self.wdir} && {cmd}" if self.wdir else cmd
        stdin, stdout, _ = self.client.exec_command(cmd, timeout=60, get_pty=True)
        stdout.channel.set_combine_stderr(True)
        while not stdout.channel.exit_status_ready():
            l = stdout.readline()
            print(l)
            try:
                stdin.write(resp)
            except:
                continue

    def close(self):
        self.client.close()
        self.client = None

    def reboot(self, timeout=300, sleep=20, initial_wait=120):
        self.run("sudo reboot")
        self.close()
        t = initial_wait
        print(f"Wait for {initial_wait}s before attempting to connect...")
        time.sleep(initial_wait)
        while True:
            try:
                print("Try connect...")
                self.connect()
                break
            except:
                if t >= timeout:
                    raise Exception(f"Timeout reached for reboot of host {self.ip}")
                time.sleep(sleep)
                print(f"Wait for {sleep}s...")
                t += sleep

