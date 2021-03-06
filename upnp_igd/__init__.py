import socket
from urllib.request import urlopen
import xml.dom.minidom as minidom
from random import randint
import logging

""" http://upnp.org/specs/gw/UPnP-gw-InternetGatewayDevice-v2-Device.pdf
Simple module for mapping and deleting port-forwards on UPnP-IGD devices
It can search for IGD devices, but it doesn't check if the required device,
service and action are available for creating port-mappings (Assumption is the mother of all f......)
UPnP standard compliance is limited/lacking
Only tested against Linux-IGD
No real error-messages are parsed/supplied, only True and False are returned/provided
"""

log = logging.getLogger('PunchVPN.UPnP-IGD')

class upnp_igd:
    def __init__(self):
        # Store for created port-mappings, used for cleaning purposes
        self._mapped_ports = {}

    def __del__(self):
        #The socket module is not available if this is __main__
        if socket:
            self.clean()

    def __exit__(self):
        #The socket module is not available if this is __main__
        if socket:
            self.clean()

    def clean(self):
        for mapping in list(self._mapped_ports):
            self.DeletePortMapping(mapping[0], mapping[1])

    
    def search(self):
        """Multicast SSDP discover, returns true if we can find an IGD device (_isIGD)"""
        log.debug('Searching for IGD devices')
        self._XML = []
        self._host = None
        #Standard multicast address and port for SSDP discover
        ip = '239.255.255.250'
        port = 1900
        searchRequest = 'M-SEARCH * HTTP/1.1\r\n'\
                            'HOST:%s:%d\r\n'\
                            'ST:upnp:rootdevice\r\n'\
                            'MX:2\r\n'\
                            'MAN:"ssdp:discover"\r\n\r\n' % (ip, port)

        #Create IPv4 UDP socket
        s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        while(1):
            try:
                s.bind(('', randint(1024, 65535)))
            except socket.error:
                # This is most lokely a binding error
                pass
            else:
                break

        s.sendto(searchRequest.encode('UTF-8'), (ip, port))
        #Don't listen for more than 5 seconds
        s.settimeout(5)
        while True:
            try:
                data, sender = s.recvfrom(2048)
                if not data:
                    break
                else:
                    data = data.decode('UTF-8')
                    if data.startswith('HTTP/1.1 200 OK'):
                        if self._isIGD(data):
                            log.debug('IGD device found')
                            return True
            except:
                #Most likely a timeout
                break
        log.debug('No IGD devices found')
        return False

    def _isIGD(self, headers):
        """ Parse headers returned by self.search(), and see if this is an IGD device """
        self._rootXML = None
        #Iterate each header
        for line in headers.split('\r\n'):
            #LOCATION indicates where the device XML is located
            if line.startswith('LOCATION:'):
                log.debug('Fetching device XML from location specified in response header\n %s' % line)
                location = line.split('LOCATION: ')[1]
                request = urlopen(location)
                xml = request.read().decode('UTF-8')
                xmlDom = minidom.parseString(xml)
                for dev in xmlDom.getElementsByTagName('device'):
                    if (dev.getElementsByTagName('deviceType')[0].childNodes[0].data.split(':')[3] ==
                    'InternetGatewayDevice'):
                        self._rootXML = xmlDom
                        host = line.split('://')[1].split('/')[0].split(':')
                        self._host = (host[0], int(host[1]))
                        return True
        return False

    def AddPortMapping(self, ip, port, protocol):
        """Adds a portmap, requires that an IGD device has been found with self.search()
        Linux IGD has a limited status reply (none really) if the syntax is correct, invalid
        port numbers etc. are not rejected. Because of this, we just return true if the HTTP
        headers status-code is 200
        There are no tests to confirm that there actually is a WANIPConn device, with an
        WANIPConnection service and an AddPortMapping action
        A mapping is stored in self._mapped_ports on success
        
        Keyword arguments:
        ip      -- string representation of the clients internal IP
        port        -- Requested port as integer
        protocol    -- Requested protocol, use 'TCP' or 'UDP'
        """

        log.debug('Mapping protocol %s port %s to host at %s' % (protocol, port, ip))
        if not self._host:
            return False
        response = ''
        #Timeconstraints did not allow creating a soap module/parser, UPnP requires NewRemoteHost,
        #NewExternalPort, NewProtocol, NewInternalPort, NewInternalClient, NewEnabled,
        #NewPortMappingDescription, NewLeaseDuration for this action

        body =  '<?xml version="1.0" encoding="UTF-8"?>'\
            '<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"\
              SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'\
                '<SOAP-ENV:Body>'\
                    '<m:AddPortMapping xmlns:m="urn:schemas-upnp-org:service:WANIPConnection:1">'\
                        '<NewLeaseDuration>0</NewLeaseDuration>'\
                        '<NewInternalClient>%s</NewInternalClient>'\
                        '<NewExternalPort>%s</NewExternalPort>'\
                        '<NewRemoteHost></NewRemoteHost>'\
                        '<NewProtocol>%s</NewProtocol>'\
                        '<NewInternalPort>%s</NewInternalPort>'\
                        '<NewPortMappingDescription>upnpigd mapping</NewPortMappingDescription>'\
                        '<NewEnabled>1</NewEnabled>'\
                    '</m:AddPortMapping>'\
                '</SOAP-ENV:Body>'\
            '</SOAP-ENV:Envelope>' % (ip, port, protocol, port)

        header =    ('POST /upnp/control/WANIPConn1 HTTP/1.1\r\n'\
                'Host:%s\r\n'\
                'Content-Length:%s\r\n'\
                'Content-Type:text/xml\r\n'\
                'SOAPAction:"urn:schemas-upnp-org:service:WANIPConnection:1#AddPortMapping"\r\n\r\n'
                % ((str(self._host[0])+':'+str(self._host[1])), len(body)))

        s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        s.connect(self._host)

        log.debug('sending SOAP request for AddPortMapping\n%s' % body)

        s.send((header+body).encode('UTF-8'))
        while True:
            data = s.recv(4096)
            if not data:
                break
            else:
                response += data.decode('UTF-8')
        log.debug('IGD device responded with \n%s' % response)
        #Look for the HTML status-code to see if everything is OK. Linux IGD soap-response had no additional
        #info, so this was faster to implement
        status = response.split('\n', 1)[0].split(' ', 2)[1] == '200'
        if status:
            log.debug('IGD device acknowledged request')
            self._mapped_ports[port, protocol] = True
        return status

    def DeletePortMapping(self, port, protocol):
        """Deletes a portmap, requires that an IGD device has been found with self.search()
        Linux IGD has a limited status reply (none really) if the syntax is correct, invalid port numbers etc.
        are not rejected. Because of this, we just return true if the HTTP headers status-code is 200
        If a mapping is present in self.__mapped_ports, it will be removed upon successfull deletion        

        Keyword arguments:
        port        -- Requested port as integer
        protocol    -- Requested protocol, use 'TCP' or 'UDP'
        """
        log.debug('Removing mapping for protocol %s and port %s' % (protocol, port))
        if not self._host:
            log.warning('No IGD device known')
            return False
        response = ''
        #Timeconstraints did not allow creating a soap module/parser, UPnP requires NewRemoteHost,
        #NewExternalPort and NewProtocol for this action
        body =  '<?xml version="1.0" encoding="UTF-8"?>'\
            '<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"\
              SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'\
                '<SOAP-ENV:Body>'\
                    '<m:DeletePortMapping xmlns:m="urn:schemas-upnp-org:service:WANIPConnection:1">'\
                        '<NewExternalPort>%s</NewExternalPort>'\
                        '<NewRemoteHost></NewRemoteHost>'\
                        '<NewProtocol>%s</NewProtocol>'\
                    '</m:DeletePortMapping>'\
                '</SOAP-ENV:Body>'\
            '</SOAP-ENV:Envelope>' % (port, protocol)

        header =    ('POST /upnp/control/WANIPConn1 HTTP/1.1\r\n'\
                'Host:%s\r\n'\
                'Content-Length:%s\r\n'\
                'Content-Type:text/xml\r\n'\
                'SOAPAction:"urn:schemas-upnp-org:service:WANIPConnection:1#DeletePortMapping"\r\n\r\n'
                % ((str(self._host[0])+':'+str(self._host[1])), len(body)))

        s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        s.connect(self._host)

        log.debug('sending SOAP request for DeletePortMapping\n%s' % body)

        s.send((header+body).encode('UTF-8'))
        while True:
            data = s.recv(4096)
            if not data:
                break
            else:
                response += data.decode('UTF-8')
        log.debug('IGD device responded with \n%s' % response)
        #Look for the HTML status-code to see if everything is OK. Linux IGD soap-response had no additional info,
        #so this was faster to implement
        status = response.split('\n', 1)[0].split(' ', 2)[1] == '200'
        if status:
             log.debug('IGD device acknowledged request')
        #Remove this tnrey from self._mapped_ports if it is present
        if status and self._mapped_ports[port, protocol]:
            del self._mapped_ports[port, protocol]
        return status

    def GetExternalIPAddress(self):
        """Asks a found IGD device for it's external ip-address"""
        
        if not self._host:
            return False
        log.debug('Requesting external ip-address')
        response = ''
        #Timeconstraints did not allow creating a soap module/parser, UPnP requires NewRemoteHost, NewExternalPort,
        #NewProtocol, NewInternalPort, NewInternalClient, NewEnabled, NewPortMappingDescription,
        #NewLeaseDuration for this action

        body =  '<?xml version="1.0" encoding="UTF-8"?>'\
            '<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"\
              SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'\
                '<SOAP-ENV:Body>'\
                    '<m:GetExternalIPAddress xmlns:m="urn:schemas-upnp-org:service:WANIPConnection:1">'\
                    '</m:GetExternalIPAddress>'\
                '</SOAP-ENV:Body>'\
            '</SOAP-ENV:Envelope>'

        header =    ('POST /upnp/control/WANIPConn1 HTTP/1.1\r\n'\
                'Host:%s\r\n'\
                'Content-Length:%s\r\n'\
                'Content-Type:text/xml\r\n'\
                'SOAPAction:"urn:schemas-upnp-org:service:WANIPConnection:1#GetExternalIPAddress"\r\n\r\n'
                % ((str(self._host[0])+':'+str(self._host[1])), len(body)))

        s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        s.connect(self._host)

        log.debug('Sending SOAP request for GetExternalIPAddress\n%s' % body)

        s.send((header+body).encode('UTF-8'))
        while True:
            data = s.recv(4096)
            if not data:
                break
            else:
                response += data.decode('UTF-8')
        log.debug('IGD device responded with \n%s' % response)
        #Look for the HTML status-code to see if everything is OK. Linux IGD soap-response had no additional
        #info, so this was faster to implement
        status = response.split('\n', 1)[0].split(' ', 2)[1] == '200'
        if status:
            log.debug('IGD device acknowledged request')
            soap_reply = response.split('\r\n\r\n')[1]
            xmlDom = minidom.parseString(soap_reply)
            ip = xmlDom.getElementsByTagName('NewExternalIPAddress')[0].childNodes[0].data
            log.debug("IGD external ip-address is %s" % ip)
            return ip
        return status
