#!/usr/bin/python3
import punchVPN
import socket
from random import randint
from punchVPN.udpKnock import udpKnock
from punchVPN.WebConnect import WebConnect
import argparse
from multiprocessing import Process
import os

parser = argparse.ArgumentParser(prog='punchVPN.py',
                                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                description='Client for making p2p VPN connections behind nat')
parser.add_argument('-p', '--peer', type=str, default=None, help='Token of your peer')
parser.add_argument('-c', '--client', action='store_true', help='Is this a client?')
parser.add_argument('-a', '--address', type=str, default='http://localhost:8080', help='What is the server address?')
parser.add_argument('--no-vpn', action='store_true', help='Run with no VPN (for debug)')
parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
args = parser.parse_args()

peer = args.peer

def log(m):
    """Add logging based on ARGS"""
    if args.verbose:
        print(m)

def startVPN(lport, raddr, rport, lVPN, rVPN):
    """Start the VPN server and wait for connection"""
    if not args.no_vpn:
        if os.name == 'posix':
            os.system("openvpn --lport "+str(lport)+" --rport "+str(rport)+" --remote "+raddr+" --dev tun1 --ifconfig "+lVPN+" "+rVPN+" --verb 9")

def startVPNclient(lport, raddr, rport):
    """Start the VPN client and connect"""
    if not args.no_vpn:
        if os.name == 'posix':
            os.system("openvpn --lport "+str(lport)+" --rport "+str(rport)+" --remote "+raddr+" --dev tun1 --ifconfig 10.4.0.2 10.4.0.1 --verb 9")

# Choose some random ports (stop "early" to be sure we get a port)
lport = randint(1025, 60000)

# Make the udpKnocker and socket. Get the maybe new lport
knocker = udpKnock(socket.socket(socket.AF_INET, socket.SOCK_DGRAM), lport)
lport = knocker.lport

# Connect to the webserver for connection and such
web = WebConnect(args.address, lport)

# Get token from server
token = web.get("/")["token"]
print("Token is: "+token)

if peer:
    """Connect and tell you want 'token'"""
    respons = web.post("/connect/",
        {'token': peer,
         'lport': lport,
         'uuid':  token})
    if respons.get('err'):
        print("Got error: "+respons['err'])
        exit()
else:
    """Connect and wait for someone to access 'token'"""
    respons = web.post("/me/",
        {'uuid': token,
         'lport' : lport})

log(respons)
raddr = respons["peer.ip"]
rport = respons["peer.lport"]
lVPNaddr = respons["me.VPNaddr"]
rVPNaddr = respons["peer.VPNaddr"]

if not peer:
    """UDP knock if needed and tell the 3rd party"""
    s = knocker.knock(raddr, int(rport))
    log(web.post("/ready/", {'uuid': token}))

knocker.s.close()
vpn = Process(target=startVPN, args=(lport, raddr, rport, lVPNaddr, rVPNaddr))
vpn.start()


vpn.join()
