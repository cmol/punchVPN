import urllib.request
import urllib.parse
import json

class WebConnect(object):
    def __init__(self, host):
        """Initialize the object, and setup some basic stuff"""
        self.host = host

    def get(self, path):
        """GET an URL, and check for status codes"""
        return self.request(path)

    def post(self, path, post_data):
        """Encode the post parameters given to json, and call self.request with the newly encoded data"""
        post_data = {'body': json.dumps(post_data)}
        return self.request(path, post_data)

    def request(self, path, data=None):
        """Request URL from the server with data if it is present.
        If the data is present, urllib uses POST to request the data, if not it uses a GET.
        Decode the respons data, and return it."""
        if data:
            respons = urllib.request.urlopen(self.host+path,urllib.parse.urlencode(data).encode('utf-8'))
        else:
            respons = urllib.request.urlopen(self.host+path)
        content = json.loads(respons.read().decode('UTF-8'))
        respons.close()
        return content
