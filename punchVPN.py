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
from natPMP import map_external_port

PRESERVES_PORT = 1
SEQUENTIAL_PORT = 2
RANDOM_PORT = 3

port_strings = {
        PRESERVES_PORT: "Preserved port allocation",
        SEQUENTIAL_PORT: "Sequential port allocation",
        RANDOM_PORT: "Random port allocation"}

def log(m):
    """Add logging based on ARGS"""
    if args.verbose:
        print(m)

def startVPN(lport, raddr, rport, lVPN, rVPN):
    """Start the VPN client and connect"""
    if not args.no_vpn:
        if os.name == 'posix':
            os.system("openvpn --lport "+str(lport)+" --rport "+str(rport)+" --remote "+raddr+" --dev tun1 --ifconfig 10.4.0.2 10.4.0.1 --verb 9")

def test_stun():
    """Get external IP address from stun, and test the connection capabilities"""
    print("STUN - Testing connection...")
    src_port=randint(1025, 65535)
    stun = get_ip_info(source_port=src_port)
    log(stun)
    port_mapping = PRESERVES_PORT if stun[2] == src_port else None

    if port_mapping != PRESERVES_PORT:
        """Test for sequential port mapping"""
        seq_stun = get_ip_info(source_port=src_port+1)
        log(seq_stun)
        port_mapping = SQUENTIAL_PORT if stun[2] + 1 == seq_stun[2] else RANDOM_PORT

    log("STUN - Port allocation: "+port_strings[port_mapping])
    seq_stun = seq_stun or None
    ret = (stun, seq_stun), port_mapping, src_port
    return ret

def main():
    """Write something clever here...."""
    post_args = {}

    """This is our methods for connecting.
    At least one of them must return true"""
    client_cap = {
            'upnp': False,
            'nat_pmp': False,
            'udp_preserve': False,
            'udp_seqential': False}

    # Choose a random port (stop "early" to be sure we get a port)
    lport = randint(1025, 60000)

    # Make the udpKnocker and socket. Get the maybe new lport
    knocker = udpKnock(socket.socket(socket.AF_INET, socket.SOCK_DGRAM), lport)
    lport = knocker.lport

    # Test the natPMP capabilities
    if not args.no_natpmp:
        print("NAT-PMP - Testing for NAT-PMP...    ")
        nat_pmp = map_external_port(lport=lport)
        if nat_pmp:
            print("NAT-PMP - [SUCCESS]")
            client_cap['nat_pmp'] = True
            external_port = nat_pmp[0]
        else:
            print("NAT-PMP - [FAILED]")

    # Get external ip-address and test what NAT type we are behind
    if not args.no_stun:
        stun, port_mapping, stun_port = test_stun()
        post_args['stun_ip'] = stun[0][1]
        if port_mapping == PRESERVES_PORT:
            client_cap['udp_preserve'] = True
        if port_mapping == SEQUENTIAL_PORT:
            client_cap['udp_seqential'] = True

    if not args.no_stun and not args.peer and port_mapping == RANDOM_PORT:
        """
        As for now, we do not have any other method of making connections for UDP traffic,
        other than udp hole punching.
        For the connection to work, both ends of the tunnel must have preserving ports.
        When UPnP, NAT-PMP, and IGD get implemented, other situations will make it easier
        to connect to eachother.
        """
        print("Sorry, you cannot connect to your peer with random port allocation :-(")
        log(client_cap)
        exit(1)
    

    # Connect to the webserver for connection and such
    web = WebConnect(args.address, lport)

    # Build a standart dict of arguments to POST
    post_args = {'lport': lport}

    # Get token from server
    token = web.get("/")["token"]
    post_args['uuid'] = token
    print("Token is: "+token)

    if args.peer:
        """Connect and tell you want 'token'"""
        post_args['token'] = args.peer
        try:
            respons = web.post("/connect/", post_args)
        except KeyboardInterrupt:
            log("Closing connection...")
            web.post("/disconnect/", post_args)
            exit(1)
        if respons.get('err'):
            print("Got error: "+respons['err'])
            exit(1)
    else:
        """Connect and wait for someone to access 'token'"""
        try:
            respons = web.post("/me/", post_args)
        except KeyboardInterrupt:
            log("Closing connection...")
            web.post("/disconnect/", post_args)
            exit(1)


    log(respons)
    raddr = respons["peer.ip"]
    rport = respons["peer.lport"]
    lVPNaddr = respons["me.VPNaddr"]
    rVPNaddr = respons["peer.VPNaddr"]

    if not args.peer:
        """UDP knock if needed and tell the 3rd party"""
        s = knocker.knock(raddr, int(rport))
        log(web.post("/ready/", {'uuid': token}))

    knocker.s.close()
    vpn = Process(target=startVPN, args=(lport, raddr, rport, lVPNaddr, rVPNaddr))
    vpn.start()


    vpn.join()

if __name__ == '__main__':
    """Runner for the script. This will hopefully allow us to compile for windows."""

    # Parse all the command line arguments, hopefully in a sane manner.
    parser = argparse.ArgumentParser(prog='punchVPN.py',
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                    description='Client for making p2p VPN connections behind nat')
    parser.add_argument('-p', '--peer', type=str, default=None, help='Token of your peer')
    parser.add_argument('-c', '--client', action='store_true', help='Is this a client?')
    parser.add_argument('-a', '--address', type=str, default='http://localhost:8080', help='What is the server address?')
    parser.add_argument('--no-vpn', action='store_true', help='Run with no VPN (for debug)')
    parser.add_argument('--no-stun', action='store_true', help='Run with no STUN')
    parser.add_argument('--no-natpmp', action='store_true', help='Run with no nat-PMP')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    args = parser.parse_args()

    # Run the main program, this is where the fun begins
    main()
