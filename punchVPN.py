#!/usr/bin/python3
import logging
logging.basicConfig()
log = logging.getLogger("PunchVPN")
import punchVPN
import socket
from random import randint
from punchVPN.udpKnock import udpKnock
from punchVPN.WebConnect import WebConnect
import argparse
from multiprocessing import Process
from time import sleep
import os
from stun import get_ip_info
from natPMP import natPMP
from upnp_igd import upnp_igd
import signal
import stat
from subprocess import call

PRESERVES_PORT = 1
SEQUENTIAL_PORT = 2
RANDOM_PORT = 3

port_strings = {
        PRESERVES_PORT: "Preserved port allocation",
        SEQUENTIAL_PORT: "Sequential port allocation",
        RANDOM_PORT: "Random port allocation"}

def startVPN(lport, raddr, rport, lVPN, rVPN, mode, key):
    """Start the VPN client and connect"""
    if not args.no_vpn:

        params = {}

        log_matrix = {
            logging.DEBUG:9,
            logging.INFO:1
        }

        try:
            loglevel = log_matrix[log.getEffectiveLevel()]
        except:
            loglevel = None

        if loglevel:
            params['--verb'] = loglevel
        else:
            params['--verb'] = 0
        
        params['--verb'] = 0

        params.update({
            '--secret':key,
            '--dev':'tap',
            '--ifconfig':'%s 255.255.255.0' % lVPN,
            '--comp-lzo':'adaptive',
            '--proto':'udp',
            '--secret':key
        })
       
        if mode == 'p2p':
            params.update({
                '--lport':str(lport),
                '--rport':str(rport),
                '--remote':raddr,
                '--ping':30,
                '--mode':mode
            })
        elif mode == 'server':
             params.update({
                '--port':str(lport),
            })
        elif mode == 'client':
            params.update({
                '--remote':raddr,
                '--port':str(rport),
                '--route-nopull':''
            })

        log.debug('Openvpn parameters: %s' % params)

        if os.name == 'posix':
            callparms = []
            for parm, value in params.items():
                callparms.append(parm)
                #TODO find another way around subproces.call encapsulating parameters with
                # "" if they contain spaces
                if parm == '--ifconfig':
                    callparms += value.split(' ')
                else:
                    callparms.append(str(value))

            call(['openvpn']+callparms)

def test_stun():
    """Get external IP address from stun, and test the connection capabilities"""
    log.info("STUN - Testing connection...")
    src_port=randint(1025, 65535)
    stun = get_ip_info(source_port=src_port)
    log.debug(stun)
    port_mapping = PRESERVES_PORT if stun[2] == src_port else None

    seq_stun = None
    if port_mapping != PRESERVES_PORT:
        """Test for sequential port mapping"""
        seq_stun = get_ip_info(source_port=src_port+1)
        log.debug(seq_stun)
        port_mapping = SQUENTIAL_PORT if stun[2] + 1 == seq_stun[2] else RANDOM_PORT

    log.debug("STUN - Port allocation: "+port_strings[port_mapping])
    seq_stun = seq_stun or None
    ret = (stun, seq_stun), port_mapping, src_port
    return ret

def find_ip(addr):
    """Find local ip to hostserver via a tmp socket.

    If the result is a local address, use 8.8.8.8 (google public dns-a) as a 
    temporary solution. This will most likely only happen during development."""
    s_ip = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s_ip.connect((addr, 1234))
    ip = s_ip.getsockname()[0]
    s_ip.close()

    # Small hacky for when running a local server, eg. when developing
    if ip.startswith('127') or ip == '0.0.0.0':
        ip = find_ip('8.8.8.8')
    return ip

def write_key(key):
    """Write the key to a file so it can me used to make a secure connection.
    To enhance security a bit, the file is firstly opened, written, closed,
    chmodded to enhance security a bit, and then the key is written to the file.

    string key

    return string path_to_key"""

    # Register globals
    global token

    # Find the OS temp dir
    if os.name == 'nt':
        path = '%temp%\\'
    else:
        path = '/tmp/'

    name = 'punchVPN-'+token+'.key'

    # Make the file a bit more secure
    f = open(path+name, 'w')
    f.write('0')
    os.chmod(path+name, stat.S_IREAD | stat.S_IWRITE)
    f.close()

    # Write the actual key to the file
    f = open(path+name, 'w')
    f.write(key)
    f.close()

    return path+name

def gracefull_shutdown(signum, frame):
    """Make a gracefull shutdown, and tell the server about it"""
    global token

    web = WebConnect(args.address)
    log.debug("Closing connection...")
    web.post('/disconnect/', {'uuid': token})
    exit(1)

def main():
    global token
    post_args = {}

    # Register a trap for a gracefull shutdown
    signal.signal(signal.SIGINT, gracefull_shutdown)

    """This is our methods for connecting.
    At least one of them must return true"""
    client_cap = {
            'upnp': False,
            'nat_pmp': False,
            'udp_preserve': False,
            'udp_sequential': False}

    # Choose a random port (stop "early" to be sure we get a port)
    lport = randint(1025, 60000)

    # Make the udpKnocker and socket. Get the maybe new lport
    knocker = udpKnock(socket.socket(socket.AF_INET, socket.SOCK_DGRAM), lport)
    lport = knocker.lport

    # Build default post_args dict, and ready a place for the external IP
    post_args = {'lport': lport}
    external_address = False

    # Test the natPMP capabilities
    if not args.no_natpmp:
        log.info("NAT-PMP - Testing for NAT-PMP...    ")
        npmp = natPMP()
        nat_pmp = npmp.map_external_port(lport=lport)
        if nat_pmp:
            log.info("NAT-PMP - [SUCCESS]")
            client_cap['nat_pmp'] = True
            post_args['lport'] = nat_pmp[0]
            external_address = npmp.get_external_address()
        else:
            log.info("NAT-PMP - [FAILED]")

    # Test the UPnP-IGD capabilities
    if not args.no_upnp and not client_cap['nat_pmp']:
        log.info("UPnP-IGD - Testing for UPnP-IDG...")

        # Find IP-Address of local machine
        # TODO: Find fix for IPv6-addresses
        ip = find_ip(args.address.split(':')[1][2:])

        # Creating the UPnP device checker
        upnp = upnp_igd()
        if upnp.search() and upnp.AddPortMapping(ip, lport, 'UDP'):
            log.info("UPnP-IGD - [SUCCESS]")
            external_address = upnp.GetExternalIPAddress()
            client_cap['upnp'] = True
        else:
            log.info("UPnP-IGD - [FAILED]")

    # Get external ip-address and test what NAT type we are behind
    if not args.no_stun and not external_address:
        stun, port_mapping, stun_port = test_stun()
        external_address = stun[0][1]
        if port_mapping == PRESERVES_PORT:
            client_cap['udp_preserve'] = True
        if port_mapping == SEQUENTIAL_PORT:
            client_cap['udp_seqential'] = True

    # Connect to the webserver for connection and such
    web = WebConnect(args.address)

    # Add client caps and external_address to post_args
    post_args['client_cap'] = client_cap
    post_args['stun_ip'] = external_address

    # Get token from server
    token = web.get('/')['token']
    post_args['uuid'] = token
    log.info("Token is: "+token)

    if args.peer:
        """Connect and tell you want 'token'"""
        post_args['token'] = args.peer
        respons = web.post('/connect/', post_args)
        if respons.get('err'):
            log.info("Got error: "+respons['err'])
            exit(1)
    else:
        """Connect and wait for someone to access 'token'"""
        respons = web.post('/me/', post_args)
        while(True):
            peer = input("Enter token of your peer: ")
            respons = web.post('/ready/', {'uuid': token, 'token': peer})
            if not respons.get('err'):
                s = knocker.knock(respons['peer.ip'], int(respons['peer.lport']))
                break

    log.debug(respons)
    raddr = respons['peer.ip']
    rport = respons['peer.lport']
    lVPNaddr = respons['me.VPNaddr']
    rVPNaddr = respons['peer.VPNaddr']
    mode = respons['me.mode']
    key = write_key(respons['me.key'])

    # Tell if we are maybe running into trouble
    if mode == 'p2p-fallback':
        log.info("Running in p2p-fallback mode, may not be able to connect...")
        sleep(2)
        mode = 'p2p'

    knocker.s.close()
    vpn = Process(target=startVPN, args=(lport, raddr, rport, lVPNaddr, rVPNaddr, mode, key))
    vpn.start()
    vpn.join()

    # Cleanup
    os.remove(key)

if __name__ == '__main__':
    """Runner for the script. This will hopefully allow us to compile for windows."""

    # Parse all the command line arguments, hopefully in a sane manner.
    parser = argparse.ArgumentParser(prog='punchVPN.py',
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                    description='Client for making p2p VPN connections behind nat')
    parser.add_argument('-p', '--peer', type=str, default=None, help='Token of your peer')
    parser.add_argument('-a', '--address', type=str, default='https://punchserver.xlaus.dk',
                        help='What is the server address? (eg. https://server-ip:443)')
    parser.add_argument('--no-vpn', action='store_true', help='Run with no VPN (for debug)')
    parser.add_argument('--no-stun', action='store_true', help='Run with no STUN')
    parser.add_argument('--no-natpmp', action='store_true', help='Run with no nat-PMP')
    parser.add_argument('--no-upnp', action='store_true', help='Run with no UPnP-IGD')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-s', '--silent', action='store_true', help='No output at all')
    args = parser.parse_args()

    if not args.silent or args.verbose:
        if args.verbose:
            log.setLevel(logging.DEBUG)
        else:
            log.setLevel(logging.INFO)

    # Run the main program, this is where the fun begins
    main()
