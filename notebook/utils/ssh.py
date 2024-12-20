import paramiko
import time
import sys
import logging

# Open
# Execute command
# Print output

class SSH:
    def __init__(self, ip, user, verbose=False):
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

    def reconnect(self):
        if not self.client:
            self.connect()
        try:
            transport = self.client.get_transport()
            transport.send_ignore()
        except EOFError:
            print(f"Attempting to reconnect to {self.ip}...")
            try:
                self.close()
            except Exception as e:
                print(f"Exception while closing before reconnect {e}")
            self.connect()

    def set_wdir(self, wdir):
        '''
        Set working directory where future commands will be executed
        (until clear_wdir is called). (Note there may be a cleaner way
        to do this with interactive shells?)
        '''
        self.wdir = wdir

    def clear_wdir(self):
        self.wdir = None

    def run(self, cmd, raise_err=True, return_stdout=False, retry=0):
        try:
            print(f"EXEC: {cmd}")
            _, stdout, _ = self.client.exec_command(f"cd {self.wdir} && {cmd}" if self.wdir else cmd)
            stdout.channel.set_combine_stderr(True)
            lines = []
            if return_stdout:
                lines = stdout.readlines()
            else:
                while not stdout.channel.exit_status_ready():
                    # Note ChannelFile built on base class BufferedFile
                    print(stdout.readline(), end="")
            exit_code = stdout.channel.recv_exit_status()
            if raise_err and exit_code != 0:
                raise Exception(f"SSH exec on {self.ip}, {cmd} return exit code {exit_code}")
            return exit_code, lines

        except Exception as e:
            if retry:
                time.sleep(1)
                print(f"Retrying (remaining={retry - 1}) after Exception {e}...")
                if any(k in str(e) for k in [
                    "is closed", "reset by", "timed out", "broken pipe"
                ]):
                    self.reconnect()
                    self.run(cmd, raise_err=raise_err, return_stdout=return_stdout, retry=retry - 1)
            raise Exception(f"SSH exec failed for {self.ip}, {cmd} with error: {e}")

    def run_with_prompts(self, cmd, resp="\n"):
        '''
        Run a command and periodically send `resp` to stdin.
        This allows us to run commands that require selecting responses to prompts
        if the response to each prompt is the same.
        '''
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

    def reboot(self, timeout=600, sleep=20, initial_wait=120):
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