"""Legacy Socket.IO transport intentionally disabled.

Order chat now uses authenticated REST endpoints in order_chat.py. The previous
socket handlers trusted a client-supplied user_id, which allowed identity
spoofing and bypassed the AI Guard. Keep this compatibility initializer so
local startup does not break, but do not register unauthenticated chat events.
"""
from flask_socketio import SocketIO

def init_chat_system(app, db):
    # REST chat is authenticated with the application's JWT and is polled by
    # the Orders UI. No public Socket.IO chat events are registered.
    return SocketIO(app, cors_allowed_origins=[])
