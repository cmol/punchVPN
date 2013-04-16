import inspect
import uuid
from gevent import monkey; monkey.patch_all()
from gevent.event import Event
from beaker.middleware import SessionMiddleware
import bottle
from bottle import route, request, static_file, template, run
from time import sleep
import json

def log(m):
    if False:
        print m

class BeakerPlugin(object):
    name = 'beaker'

    def setup(self, app):
        ''' Make sure that other installed plugins don't affect the same
            keyword argument.'''
        for other in app.plugins:
            if not isinstance(other, BeakerPlugin): continue
            if other.keyword == self.keyword:
                raise PluginError("Found another beaker session plugin "\
                "with conflicting settings (non-unique keyword).")

    def apply(self, callback, context):
        args = inspect.getargspec(context['callback'])[0]
        keyword = 'session'
        if keyword not in args:
            return callback
        def wrapper(*a, **ka):
            session = request.environ.get('beaker.session')
            ka[keyword] = session
            rv = callback(*a, **ka)
            session.save()
            return rv
        return wrapper

class Peer(object):
    def __init__(self, ip, lport):
        """Set up peer object"""
        self.ip = ip
        self.lport = lport
        self.peer = None

peers = {}
new_connect_event = Event()
new_request_event = Event()

@route('/')
def hello():
    return json.dumps({"token":str(uuid.uuid4()).split("-")[1]})

@route('/me/', method='POST')
def me():
    global new_request_event
    global peers
    post_data = json.loads(request.POST.get('body'))
    me = Peer(request.environ.get('REMOTE_ADDR'), post_data['lport'])
    peers[post_data['uuid']] = me
    while(1):
        log("Peer '"+post_data['uuid']+"' is waiting")
        new_request_event.wait()
        if me.peer:
            msg = {"peer.ip": me.peer.ip,
                   "peer.lport": me.peer.lport}
            msg = json.dumps(msg)
            return msg

@route('/connect/', method='POST')
def connect():
    global new_request_event
    global new_connect_event
    global peers
    post_data = json.loads(request.POST.get('body'))
    token = post_data['token']
    if not peers.has_key(token):
        return json.dumps({"err": "NOT_CONNECTED"})
    me = Peer(request.environ.get('REMOTE_ADDR'), post_data['lport'])
    peers[post_data['uuid']] = me
    peers[token].peer = me
    new_request_event.set()
    new_request_event.clear()
    while(1):
        log("Peer '"+post_data['uuid']+"' requested '"+token+"'")
        new_connect_event.wait()
        if me.peer:
            msg = {"peer.ip": me.peer.ip,
                   "peer.lport": me.peer.lport}
            msg = json.dumps(msg)
            del peers[post_data['uuid']]
            del peers[token]
            return msg

@route('/ready/', method='POST')
def ready():
    global new_connect_event
    global peers
    post_data = json.loads(request.POST.get('body'))
    me = peers[post_data['uuid']]
    me.peer.peer = me
    log("Peer '"+post_data['uuid']+"' is ready")
    new_connect_event.set()
    new_connect_event.clear()
    return json.dumps({"status": "OK"})

app = bottle.app()
app.install(BeakerPlugin())

session_opts = {
    'session.type': 'file',
    'session.cookie_expires': 300,
    'session.data_dir': './data',
    'session.auto': True
}
app = SessionMiddleware(app, session_opts)


if __name__ == '__main__':
    bottle.debug(True)
    bottle.run(app=app, server='gevent', host='0.0.0.0')


#run(host='localhost', port=8080, debug=True)
