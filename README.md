punchVPN
========

> Wrapper around openVPN to make p2p VPN with both peers behind nat.

**punchVPN** aims to create secure tunnels where it is normally not possible
to make tunnes without technical insight. This is done by using a
cobination of UDP hole punching, UPnP-IGD, and NAT-PMP (which is
relatively new)

All of this is done possible by having a trird party communicating port
numbers and addresses between the two (and for now, only two) clients,
and telling them where and when to connect. This third party is
**punchVPNd**. The third party is also responsible for creating the
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

When you have one of the peers connected, that peer will get a token.
Use that token with the '-p' parameter to connect to that peer as
follows:

    ./punchVPN.py -p f3ab

Other command line parameters are as follows:

    usage: punchVPN.py [-h] [-p PEER] [-a ADDRESS] [--no-vpn] [--no-stun]
                       [--no-natpmp] [--no-upnpigd] [-v] [-s]
    
    Client for making p2p VPN connections behind nat
    
    optional arguments:
      -h, --help            show this help message and exit
      -p PEER, --peer PEER  Token of your peer (default: None)
      -a ADDRESS, --address ADDRESS
                            What is the server address? (eg. https://server-
                            ip:443) (default: http://localhost:8080)
      --no-vpn              Run with no VPN (for debug) (default: False)
      --no-stun             Run with no STUN (default: False)
      --no-natpmp           Run with no nat-PMP (default: False)
      --no-upnpigd          Run with no UPnP-IGD (default: False)
      -v, --verbose         Verbose output (default: False)
      -s, --silent          No output at all (default: False)

License
=======

The the included LICENSE file for lincense info


Contributing
============

Right now, this program is developed as part of a school project.
We would love to have testers but we cannot accept other contributions for
the time being.
