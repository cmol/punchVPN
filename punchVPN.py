#!/usr/bin/python3
import punchVPN
import socket
from random import randint
from punchVPN.udpKnock import udpKnock
from punchVPN.WebConnect import WebConnect
import argparse
from multiprocessing import Process
import os
from stun import get_ip_info

def log(m):
    """Add logging based on ARGS"""
    global args
    if args.verbose:
        print(m)

def startVPN(lport, raddr, rport, lVPN, rVPN):
    """Start the VPN client and connect"""
    global args
    if not args.no_vpn:
        if os.name == 'posix':
            os.system("openvpn --lport "+str(lport)+" --rport "+str(rport)+" --remote "+raddr+" --dev tun1 --ifconfig 10.4.0.2 10.4.0.1 --verb 9")

def main():

    parser = argparse.ArgumentParser(prog='punchVPN.py',
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                    description='Client for making p2p VPN connections behind nat')
    parser.add_argument('-p', '--peer', type=str, default=None, help='Token of your peer')
    parser.add_argument('-c', '--client', action='store_true', help='Is this a client?')
    parser.add_argument('-a', '--address', type=str, default='http://localhost:8080', help='What is the server address?')
    parser.add_argument('--no-vpn', action='store_true', help='Run with no VPN (for debug)')
    parser.add_argument('--no-stun', action='store_true', help='Run with no STUN')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    global args
    args = parser.parse_args()

    peer = args.peer

    # Choose some random ports (stop "early" to be sure we get a port)
    lport = randint(1025, 60000)

    # Make the udpKnocker and socket. Get the maybe new lport
    knocker = udpKnock(socket.socket(socket.AF_INET, socket.SOCK_DGRAM), lport)
    lport = knocker.lport

    # Connect to the webserver for connection and such
    web = WebConnect(args.address, lport)

    # Build a standart dict of arguments to POST
    post_args = {'lport': lport}

    if not args.no_stun:
        """Get external IP address from stun, and test the connection capabilities"""
        print("STUN - Testing connection...")
        src_port=randint(1025, 65535)
        stun = get_ip_info(source_port=src_port)
        log(stun)
        stun_preserves_port = True if stun[2] == src_port else False
        log("STUN - Preserves port: "+str(stun_preserves_port))
        post_args['stun_ip'] = stun[1]


    if not args.no_stun and not stun_preserves_port:
        """
        As for now, we do not have any other method of making connections for UDP traffic,
        other than udp hole punching.
        For the connection to work, both ends of the tunnel must have preserving ports.
        When UPnP, NAT-PMP, and IGD get implemented, other situations will make it easier
        to connect to eachother.
        """
        print("Sorry, you need preserve port to connect to your peer :-( ...")
        exit(1)

    # Get token from server
    token = web.get("/")["token"]
    post_args['uuid'] = token
    print("Token is: "+token)

    if peer:
        """Connect and tell you want 'token'"""
        post_args['token'] = peer
        respons = web.post("/connect/", post_args)
        if respons.get('err'):
            print("Got error: "+respons['err'])
            exit()
    else:
        """Connect and wait for someone to access 'token'"""
        respons = web.post("/me/", post_args)

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

if __name__ == '__main__':
    main()
