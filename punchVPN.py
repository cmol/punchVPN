#!/usr/bin/python3
import punchVPN
import socket
import random
from punchVPN.udpKnock import udpKnock
from punchVPN.WebConnect import WebConnect

def log(m):
    print(m)

# Choose a running_ID for identification on the server
running_ID = random.randint(4096,65535)
log("RID: "+hex(running_ID))

# Choose some random ports (stop "early" to be sure we get a port)
lport = random.randint(1025, 60000)

# Make the udpKnocker and socket. Get the maybe new lport
knocker = udpKnock(socket.socket(socket.AF_INET, socket.SOCK_DGRAM), lport)
lport = knocker.lport

# Connect to the webserver for connection and such
thrdPrtyHost = "http://localhost:8080"
web = WebConnect(thrdPrtyHost, lport, running_ID)

print(web.get("/hello"))

# Use socket, and connect to the other end
raddr = "8.8.8.8"
rport = 12345
s = knocker.knock(raddr, rport)
log("rport, lport is: "+str(rport)+", "+str(lport))
