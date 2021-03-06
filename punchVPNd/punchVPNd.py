import inspect
import uuid
from gevent import monkey; monkey.patch_all()
import logging
logging.basicConfig()
log = logging.getLogger("PunchVPNd")
log.setLevel(logging.DEBUG)
from gevent.event import Event
import bottle
from bottle import route, request, static_file, template, run
from time import sleep
import json
from random import randint
from subprocess import check_output

class Peer(object):
    """Peer class for identifying the peers and creating a relation between them."""
    def __init__(self, lport):
        """Set up peer object"""
        self.ip = None
        self.lport = lport
        self.VPNaddr = None
        self.peer = None
        self.cap = None
        self.mode = None
        self.key = None

peers = {}
new_connect_event = Event()
new_request_event = Event()

@route('/')
def hello():
    """Return 2nd part of a UUID4, for a semi-uniqe token. If token is already in the
    peers list, try another one"""
    global peers
    while(True):
        token = str(uuid.uuid4()).split('-')[1]
        if not peers.get(token):
            break
    return json.dumps({'token': token})

@route('/me/', method='POST')
def me():
    """Adds the connecting peer to the peers list and waits for a
    peer wating to connect to ealier given UUID.
    This method used long polling and relies on the port specified
    by the client to be accecible throug whatever method the
    client finds usealbe."""

    # Register global vars
    global new_request_event
    global peers

    # Parse the POST data from JSON to a dict
    post_data = json.loads(request.POST.get('body'))

    # Generate keypair for the connection
    key = check_output('openvpn --genkey --secret /dev/stdout', shell=True).decode().strip()

    # Create and add object for self (me) to the peers dict
    me = Peer(post_data['lport'])
    me.ip = post_data.get('stun_ip') or request.environ.get('REMOTE_ADDR')
    me.cap = post_data['client_cap']
    me.key = key
    peers[post_data['uuid']] = me

    # Looping wait for the right client
    log.info("Peer '"+post_data['uuid']+"' is waiting")
    while(1):
        new_request_event.wait()

        # Report back the values of the matching client
        if me.peer:
            msg = {'status': 'READY'}
            msg = json.dumps(msg)
            return msg

@route('/connect/', method='POST')
def connect():
    """Tests if the connecting peer has a useable token, and
    adds the peer to the peers dict if the token is useable.
    Raises event for waiting peers that a new client is
    connected and waits for one of the waiting peers
    (identified by 'token'), to ready its connection and
    report status = ready"""

    # Register global vars
    global new_request_event
    global new_connect_event
    global peers

    # Parse the POST data from JSON to a dict and extract 'token'
    post_data = json.loads(request.POST.get('body'))
    token = post_data['token']

    # Look for peer identified by 'token' or return error to client
    if not peers.has_key(token):
        return json.dumps({'err': 'NOT_CONNECTED'})

    # Create and add self (me) to peers dict.
    # Sets peer(token).peer to self
    me = Peer(post_data['lport'])
    me.ip = post_data.get('stun_ip') or request.environ.get('REMOTE_ADDR')
    me.cap = post_data['client_cap']

    # Dertermine how we want to connect
    if peers[token].cap['upnp'] or peers[token].cap['nat_pmp']:
        me.mode = 'client'
        peers[token].mode = 'server'
    elif me.cap['upnp'] or me.cap['nat_pmp']:
        me.mode = 'server'
        peers[token].mode = 'client'
    elif ((me.cap['udp_preserve'] or me.cap['udp_sequential']) and 
        (peers[token].cap['udp_preserve'] or peers[token].cap['udp_sequential'])):
        me.mode = 'p2p'
        peers[token].mode = 'p2p'
    else:
        # For now, we'll go with trying p2p. Stun could be disabled on the client
        me.mode = 'p2p-fallback'
        peers[token].mode = 'p2p-fallback'

    peers[post_data['uuid']] = me
    peers[token].peer = me

    # Find link local addresses for useing in VPN
    c,d = str(randint(1,254)), str(randint(1,253))
    me.VPNaddr = "169.254."+c+"."+str(int(d)+1)
    peers[token].VPNaddr = "169.254."+c+"."+d

    # Raises the events for peers to wakeup and connect
    new_request_event.set()
    new_request_event.clear()

    # Looping wait for peer to return a ready connection
    log.info("Peer '"+post_data['uuid']+"' requested '"+token+"'")
    while(1):
        new_connect_event.wait()

        # Delete self and peer from peers dict.
        # return connection params
        if me.peer:
            msg = {'peer.ip': me.peer.ip,
                   'peer.lport': me.peer.lport,
                   'peer.VPNaddr': me.peer.VPNaddr,
                   'me.VPNaddr': me.VPNaddr,
                   'me.mode': me.mode,
                   'me.key': me.peer.key}
            msg = json.dumps(msg)
            del peers[post_data['uuid']]
            del peers[token]
            return msg

@route('/ready/', method='POST')
def ready():
    """Sets the peer of peer to self, and raise the
    event for the waiting connections"""

    # Register globals
    global new_connect_event
    global peers

    # Parse POST data from JSON to dict
    post_data = json.loads(request.POST.get('body'))

    # Register me, and set peer of me' peer, to me
    # Wow, that feels weird
    me = peers[post_data['uuid']]

    if peers.get(post_data['token']) == me.peer:
        msg = {'peer.ip': me.peer.ip,
               'peer.lport': me.peer.lport,
               'peer.VPNaddr': me.peer.VPNaddr,
               'me.VPNaddr': me.VPNaddr,
               'me.mode': me.mode,
               'me.key': me.key,
               'status': 'READY'}
        msg = json.dumps(msg)
        me.peer.peer = me
        log.info("Peer '"+post_data['uuid']+"' is ready")

        # Raise events for waiting connections and return ready
        new_connect_event.set()
        new_connect_event.clear()
        return msg
    else:
        return json.dumps({'err': 'NOT_CONNECTED'})

@route('/disconnect/', method='POST')
def disconnect():
    """Removes peer from peer list in event of a
    client side error or trap"""

    # Register globals
    global peers

    # Parse POST data from json to dict
    post_data = json.loads(request.POST.get('body'))

    # Look for peer to delete, and delete if it exists
    if peers.get(post_data['uuid']):
        del peers[post_data['uuid']]
        return json.dumps({"status": "OK"})
    else:
        return json.dumps({'err': 'NOT_CONNECTED'})


app = bottle.app()

if __name__ == '__main__':
    bottle.debug(True)
    bottle.run(app=app, server='gevent', host='0.0.0.0')
