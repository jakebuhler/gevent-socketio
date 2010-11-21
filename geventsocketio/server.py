import random

from gevent.pywsgi import WSGIServer
from gevent.queue import Queue
from geventsocketio.protocol import SocketIOProtocol


__all__ = ['SocketIOServer']

class SocketIOServer(WSGIServer):
    """A WSGI Server with a resource that acts like an SocketIO."""

    def __init__(self, *args, **kwargs):
        self.sessions = {}
        self.resource = kwargs.pop('resource')
        super(SocketIOServer, self).__init__(*args, **kwargs)

    def handle(self, socket, address):
        handler = self.handler_class(socket, address, self)
        self.set_environ({'socketio': SocketIOProtocol(handler)})
        handler.handle()

    def get_session(self, session_id=''):
        """Return an existing or new client Session."""

        session = self.sessions.get(session_id)

        if session is None:
            session = Session()
            self.sessions[session.session_id] = session
        else:
            session.incr_hits()

        return session


class Session(object):
    """
    Client session which checks the connection health and the queues for
    message passing.
    """

    def __init__(self):
        self.session_id = str(random.random())[2:]
        self.client_queue = Queue() # queue for messages to client
        self.server_queue = Queue() # queue for messages to server
        self.hits = 0
        self.hearbeats = 0
        self.connected = False

    def incr_hits(self):
        self.hits += 1

    def heartbeats(self):
        self.hearbeats += 1
        return self.hearbeats

    def valid_heartbeat(self, counter):
        return self.hearbeats == counter

    def is_new(self):
        return self.hits == 0

    def kill(self):
        if self.connected:
            self.connected = False
            self.server_queue.put_nowait(None)
            self.client_queue.put_nowait(None)
        else:
            raise Exception("Session already killed")

    def put_server_msg(self, msg):
        self.server_queue.put_nowait(msg)

    def put_client_msg(self, msg):
        self.client_queue.put_nowait(msg)

    def get_client_msg(self, **kwargs):
        return self.client_queue.get(**kwargs)

    def get_server_msg(self, **kwargs):
        return self.server_queue.get(**kwargs)