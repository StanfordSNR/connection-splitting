from ssh import SSH
import argparse
import re
import os


def install_linux(tag, ssh_client, docker_base):

    ## tag should be of the form `vX.YY`, `vX.YY-rcZ`, or similar.
    version = re.findall(r'\d+\.\d+', tag)[0]

    print(f"Installing Linux kernel {tag} on host {ssh_client.ip}")

    ## Set up dependencies
    print("Install dependencies...")
    ssh_client.run("sudo apt update")
    ssh_client.run("sudo apt install -y build-essential fakeroot libncurses-dev libssl-dev libelf-dev bison flex bc wget")
    # ssh_client.run("curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh")

    print(f"Cloning Linux repository at {tag}...")
    ssh_client.run("mkdir -p ~/kernel-build")
    ssh_client.set_wdir("~/kernel-build")

    exit_code, _ = ssh_client.run(f"cd linux", raise_err=False)
    if exit_code != 0:
        ssh_client.run(f"git clone --depth 1 --branch {tag} https://github.com/torvalds/linux.git")
    else:
        print("Linux directory exists; continuing...")

    ssh_client.set_wdir("~/kernel-build")
    print(f"Running setup script for Linux {tag}...")
    os.system(f"find . -name \"kernel_setup.sh\" -exec scp {{}} {ssh_client.user}@{ssh_client.ip}:~/kernel-build \\;")
    ssh_client.run("sudo chmod +x kernel_setup.sh")
    ssh_client.set_wdir("~/kernel-build")
    ssh_client.run(f"sudo sh kernel_setup.sh \"{docker_base}\"")

    print(f"Starting docker container for build...")
    os.system(f"find . -name \"kernel_build.sh\" -exec scp {{}} {ssh_client.user}@{ssh_client.ip}:~/kernel-build \\;")
    ssh_client.run("chmod +x ~/kernel-build/kernel_build.sh")
    ssh_client.run("sudo docker run --volume ~/kernel-build:/work -w /work -e HOME=/work -v ~/output:/output kernel-builder bash kernel_build.sh")

    print(f"Finishing setup...")
    ssh_client.run(f"sudo cp -r ~/output/lib/{version}* /lib/modules/")
    ssh_client.set_wdir("~/kernel-build/linux")
    ssh_client.run("sudo make install")

    # TODO GRUB UPDATE


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Linux kernel installer',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument('--host', type=str,
                        help="IP/hostname of the remote server")
    parser.add_argument('--version', type=str,
                        help="Linux branch or tag to checkout and build")
    parser.add_argument('--user', type=str, default='ubuntu',
                        help="User for remote server")
    parser.add_argument('--base', type=str, default='ubuntu:16.04',
                        help="Base docker image (\"FROM\") to use for building")
    args = parser.parse_args()

    client = SSH(args.host, args.user)
    client.connect()

    install_linux(args.version, client, args.base)

    print("Installed Linux:")
    client.run("uname -r")

    client.close()