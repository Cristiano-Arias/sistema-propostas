# -*- coding: utf-8 -*-
from app import create_app, socketio

# IMPORTANTE: Esta linha DEVE estar aqui para o Gunicorn encontrar
app = create_app()

# Socket.IO helpers: join a "room" per processo
@socketio.on("join_procurement")
def on_join_proc(data):
    proc_id = data.get("procurement_id")
    if not proc_id:
        return
    room = f"proc:{proc_id}"
    from flask_socketio import join_room
    join_room(room)


@socketio.on("join_user")
def on_join_user(data):
    user_id = data.get("user_id")
    if not user_id:
        return
    room = f"user:{user_id}"
    from flask_socketio import join_room
    join_room(room)


@socketio.on("join_role") 
def on_join_role(data):
    role = data.get("role")
    if not role:
        return
    room = f"role:{role}"
    from flask_socketio import join_room
    join_room(room)


if __name__ == "__main__":
    # For local dev: `python app.py`
    # In production (Render), gunicorn with eventlet worker is used
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
