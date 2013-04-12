from bottle import route, run
from random import randint

@route('/')
def hello():
    return hex(randint(4096, 65535))

@route('/me/<token>')
def me(token):
    return "Waiting for partner wanting token: "+token

@route('/connect/<token>')
def connect(token):
    return "Partner "+token+" is waiting for you"


run(host='localhost', port=8080, debug=True)
