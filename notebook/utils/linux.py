from ssh import SSH

def install_linux(tag, ssh_client, clone=True, linux_dir="/home/ubuntu/linux"):
    print(f"Installing Linux kernel {tag} on host {ssh_client.ip}")

    # Set up dependencies
    print("Install dependencies...")
    ssh_client.run("sudo apt update")
    ssh_client.run("sudo apt install -f build-essential fakeroot libncurses-dev libssl-dev libelf-dev bison flex bc wget")

    # Get folder where repository will go
    exit_code, _ = ssh_client.run(f"cd {linux_dir}", raise_err=False)
    if clone and exit_code == 0:
        raise Exception(f"Linux directory already exists on {ssh_client.ip}")
    elif not clone and exit_code != 0:
        raise Exception(f"Linux directory does not exist on {ssh_client.ip}")

    # Download
    if clone:
        print("Cloning repository...")
        ssh_client.run(f"git clone --depth 1 --branch {tag} https://github.com/torvalds/linux.git")
    else:
        print("Git checkout...")
        ssh_client.run(f"cd {linux_dir} && git checkout {tag}")

    ssh_client.set_wdir(linux_dir)

    # Set up build
    ssh_client.run("cp /boot/config-$(uname -r) .config")
    ssh_client.run_with_prompts("openssl req -x509 -newkey rsa:4096 -keyout certs/mycert.pem -out certs/mycert.pem -nodes -days 3650")
    ssh_client.run_with_prompts("make oldconfig")
    cmd = f"sed -i 's@CONFIG_MODULE_SIG_KEY=\"certs/signing_key.pem\"@CONFIG_MODULE_SIG_KEY=\"certs/mycert.pem\"@' .config"
    ssh_client.run(cmd)
    cmd = f"sed -i 's@^CONFIG_SYSTEM_TRUSTED_KEYS=.*$@CONFIG_SYSTEM_TRUSTED_KEYS=\"\"@' .config"
    ssh_client.run(cmd)
    cmd = f"sed -i 's@^CONFIG_SYSTEM_REVOCATION_KEYS=.*$@CONFIG_SYSTEM_REVOCATION_KEYS=\"\"@' .config"
    ssh_client.run(cmd)

    ssh_client.run("scripts/config --disable DEBUG_INFO")
    ssh_client.run("scripts/config --disable DEBUG_INFO_DWARF5")

    # Make
    print("Build...")
    ssh_client.run("make -j$(nproc)")
    print("Done with make")

    # Install
    print("Install...")
    ssh_client.run("sudo make modules_install")
    print("Done installing modules")
    ssh_client.run("sudo make install")
    print("Done make install")
    ssh_client.run("sudo update-grub")

    ssh_client.clear_wdir(linux_dir)

    # Reboot
    print(f"Rebooting {ssh_client.ip}...")
    ssh_client.reboot()

    # Check version
    print(f"Installation of {tag} complete on {ssh_client.ip}")
    ssh_client.run("uname -r")
