#!/usr/bin/python3
import punchVPN
import socket
from random import randint
from punchVPN.udpKnock import udpKnock
from punchVPN.WebConnect import WebConnect
import argparse

parser = argparse.ArgumentParser(prog='snake.py',
                                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                description='Small snake game for many players')
parser.add_argument('-p', '--peer', type=str, default=None, help='Token of your peer')
parser.add_argument('-c', '--client', action='store_true', help='Is this a client?')
parser.add_argument('-a', '--address', type=str, default='http://localhost:8080', help='What is the server address?')
args = parser.parse_args()

peer = args.peer

def log(m):
    print(m)

# Choose some random ports (stop "early" to be sure we get a port)
lport = randint(1025, 60000)

# Make the udpKnocker and socket. Get the maybe new lport
knocker = udpKnock(socket.socket(socket.AF_INET, socket.SOCK_DGRAM), lport)
lport = knocker.lport

# Connect to the webserver for connection and such
thrdPrtyHost = "http://localhost:8080"
web = WebConnect(thrdPrtyHost, lport)

token = web.get("/")
log(token)

if peer:
    log(web.post("/connect/",
        {'token': peer,
         'lport': lport,
         'uuid':  token}))
    """This is where we are supposed to start the openVPN client"""
else:
    log(web.post("/me/",
        {'uuid': token,
         'lport' : lport}))
    """This is where we are supposed to port knock, and start the openVPN server"""
    log(web.post("/ready/",
        {'uuid': token}))

# Use socket, and connect to the other end
raddr = "8.8.8.8"
rport = 12345
s = knocker.knock(raddr, rport)
#log("rport, lport is: "+str(rport)+", "+str(lport))
