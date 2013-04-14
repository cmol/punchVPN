import urllib.request
import urllib.parse

class WebConnect(object):
    def __init__(self, host, lport):
        """Initialize the object, and setup some basic stuff"""
        self.host = host
        self.lport = lport

    def get(self, path):
        """GET an URL, and check for status codes"""
        return self.request(path)

    def post(self, path, post_data):
        return self.request(path, post_data)

    def request(self, path, data=None):
        if data:
            respons = urllib.request.urlopen(self.host+path,urllib.parse.urlencode(data).encode('utf-8'))
        else:
            respons = urllib.request.urlopen(self.host+path)
        content = respons.read().decode("UTF-8")
        respons.close()
        return content
