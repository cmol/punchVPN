import socket
import errno

class udpKnock(object):
    def __init__(self, s, lport):
        """Try binding the port given as lport. If it fails, try the
        lport + 1, and continue to add 1 to lport, untill it succeeds."""
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
        Send some garbage data to $addr to perform the udp knocking."""
        self.s.connect((addr, rport))
        self.s.sendto(bytes('knock knock', 'UTF-8'), (addr, rport))
        return self.s
