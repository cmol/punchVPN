import socket
import errno

class udpKnock:
    @staticmethod
    def knock(s, addr, lport, rport):
        """Connect to $addr with lport as local port.
        Try until a port is useable"""
        while(1):
            try:
                s.bind(('', lport))
            except socket.error as e:
                 if e.errno != errno.EADDRINUSE:
                     raise e
                 lport+=1
            else:
                s.connect((addr, rport))
                return s, lport
