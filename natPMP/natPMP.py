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
from struct import pack, unpack
import logging

log = logging.getLogger('PunchVPN.nat-pmp')

class natPMP:

    def __init__(self):
        """Make a list to store the mapped ports"""
        self.mapped_ports = {}
        self.gateway = self.determine_gateway()

    def __del__(self):
        self.cleanup()

    def __exit__(self):
        self.cleanup()

    def cleanup(self):
        if socket and len(self.mapped_ports) > 0:
            for mapping in list(self.mapped_ports):
                log.info('Delete mapping for port ' + mapping[1])
                self.map_external_port(lport=mapping[0], external_port=0, timeout=0)

    def create_payload(self, local_port, external_port, lifetime):
        """Create the natPMP payload for opening 'external_port'
        (0 means that the GW will choose one randomly) and
        redirecting the traffic to client machine.

        int local_port
        int external_port (optional)

        return int payload
        """

        return pack('>2B3HI', 0, 1, 0, local_port, external_port, lifetime)

    def send_payload(self, s, payload, gateway):
        """Encode and send the payload to the gateway of the network

        socket s
        int payload
        string gateway

        return bool success
        """
        try:
            s.sendto(payload, (gateway, 5351))
            success = True
        except socket.error as err:
            if err.errno != errno.ECONNREFUSED:
                raise err
            success = False

        return success

    def parse_respons(self, payload):
        """Parse the respons from the natPMP device (if any).

        string respons

        return tuple (external_port, lifetime) or False
        """

        values = unpack('>2BHI2HI', payload)
        if values[2] != 0:
            """In this case, we get a status code back and can assume
            that we are dealing with a natPMP capable gateway.
            If the status code is anything other than 0, setting the
            external port failed."""
            return False

        # Get lifetime and port using bitmasking
        lifetime = values[6]
        external_port = values[5]

        return external_port, lifetime

    def determine_gateway(self):
        """Determine the gateway of the network as it is
        most likely here we will find a natPMP enabled device.

        return string gatweay
        """

        if os.name == 'posix':
            default_gateway = check_output("ip route | awk '/default/ {print $3}'", shell=True).decode().strip()

        if os.name == 'mac':
            """NOT TESTED"""
            default_gateway = check_output("/usr/sbin/netstat -nr | grep default | awk '{print $2}'", shell=True).decode().strip()

        if os.name == 'nt':
            """Use WMI for finding the default gateway if we are on windows"""
            import wmi
            wmi_obj = wmi.WMI()
            wmi_sql = "select DefaultIPGateway from Win32_NetworkAdapterConfiguration where IPEnabled=TRUE"
            wmi_out = wmi_obj.query( wmi_sql )

            for dev in wmi_out:
                default_gateway = dev.DefaultIPGateway[0]

        log.debug('Found gateway ' + default_gateway)

        return default_gateway

    def map_external_port(self, lport=random.randint(1025,65535), external_port=0, timeout=7200):
        """Try mapping an external port to an internal port via the natPMP spec
        This will also test if the gateway is capable of doing natPMP (timeout based),
        and determine the default gateway.

        It is highly recommended that the lport is provided and bound in advance,
        as this module will not test if the port is bindable, and will not return the lport.

        If the timeout is set to 0 the mapping will be destroid. In this case the external
        port must also be set to 0 and from the draft, is seems that the lport must be the
        same as in the time of creation.

        int lport
        int external_port
        int timeout

        return tuple(external_port, timeout) or False"""

        stimeout = .25

        payload = self.create_payload(lport, external_port, timeout)

        while stimeout < 6:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.bind(('',random.randint(1025, 65535)))
            s.settimeout(stimeout)

            if self.send_payload(s, payload, self.gateway):
                try:
                    rpayload = s.recvfrom(4096)
                except socket.error as err:
                    if (err.errno and err.errno != errno.ETIMEDOUT) or str(err) != 'timed out':
                        """For some reason, the timed out error have no errno, although the
                        errno atrribute is existing (set to None). For this reason, we get this
                        weird error handeling. It might be a bug in python3.2.3"""
                        raise err
                    s = None
                else:
                    if rpayload[1][0] == self.gateway:
                        if timeout == 0:
                            del self.mapped_ports[lport]
                            return True
                        else:
                            log.debug('Mapping port ' + respons[0])
                            respons = self.parse_respons(rpayload[0])
                            self.mapped_ports[lport] = (lport, respons[0], respons[1])
                            return respons

            stimeout = stimeout * 2

        log.debug('Gateway '+self.gateway+' does not support nat-pmp')
        return False

if __name__ == '__main__':
    npmp = natPMP()
    print(npmp.map_external_port(lport=12345))
