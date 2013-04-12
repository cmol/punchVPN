import urllib.request

class WebConnect(object):
    def __init__(self, host, lport):
        """Initialize the object, and setup some basic stuff"""
        self.host = host
        self.lport = lport

    def get(self, path):
        """GET an URL, and check for status codes"""
        respons = urllib.request.urlopen(self.host+path)
        content = respons.read().decode("UTF-8")
        respons.close()
        return content
