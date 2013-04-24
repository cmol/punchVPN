punchVPN
========

> Wrapper around openVPN to make p2p VPN with both peers behind nat.

*punchVPN* aims to create secure tunnels where it is normally not possible
to make tunnes without technical insight. This is done by using a
cobination of UDP hole punching, UPnP-IGD, and NAT-PMP (which is
relatively new)

All of this is done possible by having a trird party communicating port
numbers and addresses between the two (and for now, only two) clients,
and telling them where and when to connect. This third party is
*punchVPNd*. The third party is also responsible for creating the
symmetric keys shared among the clients.

Usage:
------

### Server - punchVPNd ###

The server runs with python2.7 and above and not python3 for now. This is due to
me not figuring out how to get gevent and greenlets run on python3.

Run the server with:

    python punchVPNd.py

assuming that python2 is your default python.
The server will listen on http port 8080, and since the keys are being
sent across this channel, you will need to place a reverse proxy in
front of it, such as apache or nginx, with SSL enabled.

### Client - punchVPN ###

The client runs with python3.2 and newer and is run with:

    ./punchVPN.py

If you do not have a python3 installation this will fail.
