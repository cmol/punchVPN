class UdpStater(object):

    def __init__(self):
        """initializer, must be here"""

    def dst_is(self,tst_dst):
        """Finds and returnes the first src, dst pair
        where dst_ip is first argument"""
        f = self.__read_states()
        f.pop(0)
        for line in f:
            src = self.__parse_addr(line.split(" ")[2].split(":"))
            dst = self.__parse_addr(line.split(" ")[3].split(":"))
            
            src = ".".join(src[0].split(".")[::-1]), src[1]

            if dst[0] == tst_dst:
                return src, dst

    def __parse_addr(self, addr):
        """Translate adress and port from hex to dec"""
        ip, port = addr[0], addr[1]
        ip_parsed = str(int(ip[0:2], 16))+"."+str(int(ip[2:4], 16))+"."+str(int(ip[4:6], 16))+"."+str(int(ip[6:8], 16))
        port_parsed = int(port, 16)
        return ip_parsed, port_parsed

    def __read_states(self):
        """open /proc/net/udp and split it into a list"""
        with open("/proc/net/udp") as f:
            return f.readlines()
