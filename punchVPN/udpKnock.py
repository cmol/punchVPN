import socket
import time
import os

class udpKnock(object):

    def __init__(self):
        """docstring for __init__"""
        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except socket.error:
            print "failed to create socket"
            exit()

    def knock(self, addr, port):
        """Open an UDP connection to $addr on dst port $port"""
        #self.s.sendto("wafande", (addr, port))
        os.system("echo \"WTF\" | nc -u "+addr+" "+str(port))
