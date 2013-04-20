"""
Script for requesting a port redirection via natPMP.
Follows the standart of:
http://tools.ietf.org/html/draft-cheshire-nat-pmp-07#section-3.3
with the exception of hold times. We are not going to wait a little
above 3 minutes to test for natPMP.
"""

import socket
import random
import errno
import os
from subprocess import check_output

def create_payload(local_port, external_port, lifetime):
    """Create the natPMP payload for opening 'external_port'
    (0 means that the GW will choose one randomly) and
    redirecting the traffic to client machine.
    
    int local_port
    int external_port (optional)
    
    return int payload
    """

    return int(
            bin(int("0", 10))[2:].zfill(8)+                 # Version
            bin(int("1", 10))[2:].zfill(8)+                 # Map UDP
            bin(int("0", 10))[2:].zfill(16)+                # Reserved
            bin(int(str(local_port), 10))[2:].zfill(16)+    # local_port
            bin(int(str(external_port), 10))[2:].zfill(16)+ # external_port
            bin(int(str(lifetime), 10))[2:].zfill(32)       # Lifetime of forwarding
            , 2)

def send_payload(s, payload, gateway):
    """Encode and send the payload to the gateway of the network
    
    socket s
    int payload
    string gateway
    
    return bool success
    """
    try:
        s.sendto(payload.to_bytes(12,'big'), (gateway, 5351))
        success = True
    except socket.error as err:
        if err.errno != errno.ECONNREFUSED:
            raise err
        success = False

    return success

def parse_respons(payload):
    """Parse the respons from the natPMP device (if any).
    
    string respons
    
    return tuple (external_port, lifetime) or False
    """
    payload = payload.from_bytes(16, 'big')
    if payload & 0x0000ffff000000000000000000000000 != 0:
        """In this case, we get a status code back and can assume
        that we are dealing with a natPMP capable gateway.
        If the status code is anything other than 0, setting the
        external port failed."""
        return False

    # Get lifetime and port using bitmasking
    lifetime = payload & 0x000000000000000000000000ffffffff
    external_port = (payload & 0x00000000000000000000ffff00000000) >> 32

    return external_port, lifetime

def determine_gateway():
    """Determine the gateway of the network as it is
    most likely here we will find a natPMP enabled device.
    
    return string gatweay
    """

    if os.name == 'posix':
        default_gateway = check_output("ip route | awk '/default/ {print $3}'", shell=True).decode().strip()

    if os.name == 'mac':
        """NOT TESTED"""
        default_gateway = check_output("netstat -nr | grep default | awk '{print $2}'", shell=True).decode().strip()
    
    if os.name == 'nt':
        """Use WMI for finding the default gateway if we are on windows
        NOT TESTED YET"""
        import wmi
        wmi_obj = wmi.WMI()
        wmi_sql = "select DefaultIPGateway from Win32_NetworkAdapterConfiguration where IPEnabled=TRUE"
        wmi_out = wmi_obj.query( wmi_sql )

        for dev in wmi_out:
            default_gateway = dev.DefaultIPGateway[0]

    return default_gateway

def map_external_port(lport=random.randint(1025,65535), external_port=0, timeout=7200):
    """Try mapping an external port to an internal port via the natPMP spec
    This will also test if the gateway is capable of doing natPMP (timeout based),
    and determine the default gateway.
    
    It is highly recommended that the lport is provided and bound in advance,
    as this module will not test if the port is bindable"""
    
    gateway = determine_gateway()
    stimeout = .25

    payload = create_payload(lport, external_port, timeout)

    while stimeout < 6:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(('',random.randint(1025, 65535)))
        s.settimeout(stimeout)

        if send_payload(s, payload, gateway):
            try:
                rpayload = s.recvfrom(4096)
            except socket.error as err:
                if (err.errno and err.errno != errno.ETIMEDOUT) or str(err) != 'timed out':
                    raise err
                s = None
            else:
                if rpayload[1][0] == gateway:
                    return parse_respons(rpayload[0])

        stimeout = stimeout * 2

    return False

if __name__ == '__main__':
    print(map_external_port())
