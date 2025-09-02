# -*- coding: utf-8 -*-
"""
Arquivo principal da aplicação
"""
# IMPORTANTE: eventlet.monkey_patch() DEVE ser a primeira coisa
import eventlet
eventlet.monkey_patch()

from app import create_app, socketio
from flask_socketio import join_room

# Criar a aplicação Flask
application = create_app()
app = application  # Alias para compatibilidade com Gunicorn

# Socket.IO event handlers
@socketio.on("join_procurement")
def on_join_proc(data):
    proc_id = data.get("procurement_id")
    if not proc_id:
        return
    room = f"proc:{proc_id}"
    join_room(room)


@socketio.on("join_user")
def on_join_user(data):
    user_id = data.get("user_id")
    if not user_id:
        return
    room = f"user:{user_id}"
    join_room(room)


@socketio.on("join_role") 
def on_join_role(data):
    role = data.get("role")
    if not role:
        return
    room = f"role:{role}"
    join_room(room)


if __name__ == "__main__":
    # Para desenvolvimento local
    socketio.run(application, host="0.0.0.0", port=5000, debug=False)
