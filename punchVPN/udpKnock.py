import socket
import errno

class udpKnock(object):
    
    def __init__(self, s, lport):
        """docstring for __init__"""
        while(1):
            try:
                s.bind(('', lport))
                break
            except socket.error as e:
                 if e.errno != errno.EADDRINUSE:
                     raise e
                 lport+=1
        self.lport = lport
        self.s = s

    def lport(self):
        return self.lport

    def knock(self, addr, rport):
        """Connect to $addr with lport as local port.
        Try until a port is useable"""
        self.s.connect((addr, rport))
        self.s.sendto(bytes('knock knock', 'UTF-8'), (addr, rport))
        return self.s
