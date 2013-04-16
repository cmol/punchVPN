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
    if args.verbose:
        print(m)

def startVPNserver(lport, raddr, rport):
    """Start the VPN server and wait for connection"""
    if not args.no_vpn:
        if os.name == 'posix':
            os.system("openvpn --lport "+str(lport)+" --rport "+str(rport)+" --remote "+raddr+" --dev tun1 --ifconfig 10.4.0.1 10.4.0.2 --verb 9")

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

token = web.get("/")["token"]
print("Token is: "+token)

if peer:
    respons = web.post("/connect/",
        {'token': peer,
         'lport': lport,
         'uuid':  token})
    log(respons)
    if respons.get('err'):
        print("Got error: "+respons['err'])
        exit()
    raddr = respons["peer.ip"]
    rport = respons["peer.lport"]
    """This is where we are supposed to start the openVPN client"""
    knocker.s.close()
    vpn = Process(target=startVPNclient, args=(lport, raddr, rport))
    vpn.start()
else:
    respons = web.post("/me/",
        {'uuid': token,
         'lport' : lport})
    log(respons)
    raddr = respons["peer.ip"]
    rport = respons["peer.lport"]
    s = knocker.knock(raddr, int(rport))
    s.close()
    vpn = Process(target=startVPNserver, args=(lport, raddr, rport))
    vpn.start()
    """This is where we are supposed to port knock, and start the openVPN server"""
    log(web.post("/ready/",
        {'uuid': token}))


vpn.join()
# Use socket, and connect to the other end
#raddr = "8.8.8.8"
#rport = 12345
#s = knocker.knock(raddr, rport)
#log("rport, lport is: "+str(rport)+", "+str(lport))
