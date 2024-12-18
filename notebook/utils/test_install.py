from ssh import SSH
from linux import *

client = SSH("16.171.5.214")
client.connect()

install_linux("v6.5", client, clone=False)

print("Installed Linux:")
client.run("uname -r")

client.close()