# app.py
import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sock import Sock
from itsdangerous import URLSafeSerializer
from db import get_cursor
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")
sock = Sock(app)

serializer = URLSafeSerializer(app.secret_key, salt="user")

# In-Memory Signaling-Rooms (MVP)
signal_rooms = {}

@app.route("/")
def index():
    user_id = session.get("uid")
    if not user_id:
        # Create guest user (simplified MVP)
        with get_cursor(commit=True) as cur:
            cur.execute("INSERT INTO app_user (email, onboarding_done) VALUES (%s, TRUE) RETURNING id", (None,))
            row = cur.fetchone()
            session["uid"] = str(row["id"])
        user_id = session["uid"]
        print(f"👤 New user created: {user_id[:8]}")
    
    # Check if user has a recent active session (within last 5 minutes)
    with get_cursor() as cur:
        cur.execute("""
            SELECT cs.id, cs.ice_room_key 
            FROM conversation_session cs
            JOIN session_participant sp ON cs.id = sp.session_id
            WHERE sp.user_id = %s AND cs.status != 'ended'
            AND cs.created_at > now() - interval '5 minutes'
            ORDER BY cs.created_at DESC
            LIMIT 1
        """, (user_id,))
        active_session = cur.fetchone()
        
        # Check if user is in queue
        cur.execute("SELECT user_id FROM match_queue WHERE user_id = %s", (user_id,))
        in_queue = cur.fetchone()
        
        # Check profile completion
        cur.execute("SELECT profile_completed FROM app_user WHERE id = %s", (user_id,))
        profile_result = cur.fetchone()
        profile_completed = profile_result['profile_completed'] if profile_result else False
    
    return render_template("index.html", 
                         active_session=active_session, 
                         in_queue=bool(in_queue),
                         user_id_short=user_id[:8],
                         profile_completed=profile_completed)

@app.post("/enqueue")
def enqueue():
    user_id = session.get("uid")
    if not user_id:
        return redirect(url_for("index"))
        
    mood = request.form.get("mood", "neutral")
    style = request.form.get("style", "deep")
    lang = request.form.get("lang", "de")
    
    with get_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO match_queue(user_id, mood, style, lang)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET 
                mood=EXCLUDED.mood, 
                style=EXCLUDED.style, 
                lang=EXCLUDED.lang, 
                enqueued_at=now()
        """, (user_id, mood, style, lang))
        
        # Check how many are waiting
        cur.execute("SELECT COUNT(*) as count FROM match_queue")
        total_waiting = cur.fetchone()['count']
        
    print(f"📝 User {user_id[:8]} joined queue. Total waiting: {total_waiting}")
    return redirect(url_for("match"))

@app.get("/match")
def match():
    user_id = session.get("uid")
    if not user_id:
        return redirect(url_for("index"))
    
    with get_cursor(commit=True) as cur:
        # First, check if user already has a RECENT active session (within last 5 minutes)
        cur.execute("""
            SELECT cs.id, cs.ice_room_key 
            FROM conversation_session cs
            JOIN session_participant sp ON cs.id = sp.session_id
            WHERE sp.user_id = %s AND cs.status != 'ended'
            AND cs.created_at > now() - interval '5 minutes'
            ORDER BY cs.created_at DESC
            LIMIT 1
        """, (user_id,))
        existing_session = cur.fetchone()
        
        if existing_session:
            print(f"🔄 User {user_id[:8]} rejoining recent session {existing_session['id']}")
            return redirect(url_for("session_view", sid=existing_session['id']))
        
        # Check if current user is in queue
        cur.execute("SELECT user_id FROM match_queue WHERE user_id = %s", (user_id,))
        current_user_in_queue = cur.fetchone()
        
        if not current_user_in_queue:
            # User is not in queue and has no active session, redirect to homepage
            return redirect(url_for("index"))
        
        # Look for another user in queue (not ourselves)
        cur.execute("""
            SELECT user_id FROM match_queue
            WHERE user_id <> %s
            ORDER BY enqueued_at ASC
            LIMIT 1
        """, (user_id,))
        cand = cur.fetchone()
        
        if not cand:
            # No other user waiting, show waiting screen
            cur.execute("SELECT COUNT(*) as total FROM match_queue")
            total_waiting = cur.fetchone()['total']
            return render_template("match.html", waiting=True, queue_position=1, total_waiting=total_waiting)
        
        other_id = cand["user_id"]
        
        # Create session
        room_key = uuid.uuid4().hex
        cur.execute("""
            INSERT INTO conversation_session (status, lang, style, ice_room_key)
            VALUES ('initiated', 'de', 'deep', %s)
            RETURNING id
        """, (room_key,))
        srow = cur.fetchone()
        sid = srow["id"]
        
        # Add participants
        cur.execute("INSERT INTO session_participant (session_id, user_id, joined_at) VALUES (%s, %s, now())", (sid, user_id))
        cur.execute("INSERT INTO session_participant (session_id, user_id, joined_at) VALUES (%s, %s, now())", (sid, other_id))
        
        # Remove both users from queue
        cur.execute("DELETE FROM match_queue WHERE user_id IN (%s,%s)", (user_id, other_id))
        
        print(f"🎯 Match created! Users {user_id[:8]} and {other_id[:8]} -> Session {sid}")
    
    return redirect(url_for("session_view", sid=sid))

@app.get("/session/<uuid:sid>")
def session_view(sid):
    # Conversation Cards fürs UI ziehen
    with get_cursor() as cur:
        cur.execute("SELECT id, topic, depth, prompt FROM conversation_card ORDER BY depth DESC, id ASC LIMIT 10")
        cards = cur.fetchall()
        cur.execute("SELECT ice_room_key FROM conversation_session WHERE id=%s", (str(sid),))
        row = cur.fetchone()
    return render_template("session.html", sid=str(sid), room_key=row["ice_room_key"], cards=cards, stun=os.getenv("STUN_URL","stun:stun.l.google.com:19302"))

@app.post("/session/<uuid:sid>/end")
def end_session(sid):
    user_id = session.get("uid")
    if not user_id:
        return {"error": "Not authenticated"}, 401
    
    with get_cursor(commit=True) as cur:
        # Verify user is part of this session
        cur.execute("""
            SELECT session_id FROM session_participant 
            WHERE session_id = %s AND user_id = %s
        """, (str(sid), user_id))
        
        if not cur.fetchone():
            return {"error": "Access denied"}, 403
        
        # End the session
        cur.execute("""
            UPDATE conversation_session 
            SET status = 'aborted', ended_at = now()
            WHERE id = %s
        """, (str(sid),))
        
        print(f"🔚 Session {str(sid)[:8]} ended by user {user_id[:8]}")
    
    return {"success": True}

@app.get("/session/<uuid:sid>/messages")
def get_chat_messages_ajax(sid):
    user_id = session.get("uid")
    if not user_id:
        return {"error": "Not authenticated"}, 401
    
    connection_id = session.get("active_connection")
    if not connection_id:
        return {"messages": []}
    
    with get_cursor() as cur:
        # Get messages with sender info
        cur.execute("""
            SELECT cm.id, cm.sender_id, cm.message, cm.timestamp,
                   u.first_name, u.avatar_emoji
            FROM chat_message cm
            JOIN users u ON u.id = cm.sender_id
            WHERE cm.connection_id = %s
            ORDER BY cm.timestamp
        """, (connection_id,))
        
        messages = []
        for msg in cur.fetchall():
            is_own = msg["sender_id"] == user_id
            messages.append({
                "id": msg["id"],
                "message": msg["message"],
                "timestamp": msg["timestamp"].strftime("%H:%M"),
                "sender_name": "Du" if is_own else msg["first_name"],
                "avatar": msg["avatar_emoji"],
                "is_own": is_own
            })
    
    return {"messages": messages}

@app.get("/profile")
def profile():
    user_id = session.get("uid")
    if not user_id:
        return redirect(url_for("index"))
    
    with get_cursor() as cur:
        cur.execute("""
            SELECT id, nickname, bio, profile_completed, display_name
            FROM app_user WHERE id = %s
        """, (user_id,))
        user = cur.fetchone()
    
    return render_template("profile.html", user=user)

@app.post("/profile")
def update_profile():
    user_id = session.get("uid")
    if not user_id:
        return redirect(url_for("index"))
    
    nickname = request.form.get("nickname", "").strip()
    bio = request.form.get("bio", "").strip()
    
    if not nickname:
        return render_template("profile.html", error="Nickname ist erforderlich", user={"nickname": "", "bio": bio})
    
    with get_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE app_user 
            SET nickname = %s, bio = %s, profile_completed = TRUE
            WHERE id = %s
        """, (nickname, bio, user_id))
    
    return redirect(url_for("profile"))

@app.get("/connections")
def connections():
    user_id = session.get("uid")
    if not user_id:
        return redirect(url_for("index"))
    
    with get_cursor() as cur:
        # Get all connections for this user with latest message info
        cur.execute("""
            SELECT 
                uc.id as connection_id,
                uc.connected_at,
                uc.session_id,
                uc.last_activity,
                uc.chat_active,
                other_user.nickname,
                other_user.bio,
                other_user.id as other_user_id,
                latest_msg.message as last_message,
                latest_msg.sent_at as last_message_at,
                latest_msg.sender_id = %s as last_message_from_me,
                unread_count.count as unread_count
            FROM user_connection uc
            JOIN app_user other_user ON (
                CASE 
                    WHEN uc.user1_id = %s THEN uc.user2_id = other_user.id
                    ELSE uc.user1_id = other_user.id
                END
            )
            LEFT JOIN LATERAL (
                SELECT message, sent_at, sender_id 
                FROM chat_message 
                WHERE connection_id = uc.id 
                ORDER BY sent_at DESC 
                LIMIT 1
            ) latest_msg ON true
            LEFT JOIN LATERAL (
                SELECT COUNT(*) as count
                FROM chat_message 
                WHERE connection_id = uc.id 
                AND sender_id != %s 
                AND read_at IS NULL
            ) unread_count ON true
            WHERE uc.user1_id = %s OR uc.user2_id = %s
            ORDER BY COALESCE(uc.last_activity, uc.connected_at) DESC
        """, (user_id, user_id, user_id, user_id, user_id))
        connections_list = cur.fetchall()
    
    return render_template("connections.html", connections=connections_list)

@app.get("/chat/<int:connection_id>")
def chat_view(connection_id):
    user_id = session.get("uid")
    if not user_id:
        return redirect(url_for("index"))
    
    with get_cursor(commit=True) as cur:
        # Verify user is part of this connection
        cur.execute("""
            SELECT 
                uc.id,
                other_user.nickname,
                other_user.bio,
                other_user.id as other_user_id
            FROM user_connection uc
            JOIN app_user other_user ON (
                CASE 
                    WHEN uc.user1_id = %s THEN uc.user2_id = other_user.id
                    ELSE uc.user1_id = other_user.id
                END
            )
            WHERE uc.id = %s AND (uc.user1_id = %s OR uc.user2_id = %s)
        """, (user_id, connection_id, user_id, user_id))
        
        connection = cur.fetchone()
        if not connection:
            return redirect(url_for("connections"))
        
        # Get chat messages
        cur.execute("""
            SELECT 
                cm.id,
                cm.message,
                cm.sent_at,
                cm.sender_id,
                sender.nickname as sender_nickname,
                cm.sender_id = %s as is_me
            FROM chat_message cm
            JOIN app_user sender ON cm.sender_id = sender.id
            WHERE cm.connection_id = %s
            ORDER BY cm.sent_at ASC
        """, (user_id, connection_id))
        messages = cur.fetchall()
        
        # Mark messages as read
        cur.execute("""
            UPDATE chat_message 
            SET read_at = now() 
            WHERE connection_id = %s 
            AND sender_id != %s 
            AND read_at IS NULL
        """, (connection_id, user_id))
        
        # Update last activity
        cur.execute("""
            UPDATE user_connection 
            SET last_activity = now() 
            WHERE id = %s
        """, (connection_id,))
    
    return render_template("chat.html", 
                         connection=connection, 
                         messages=messages,
                         connection_id=connection_id)

@app.get("/chat/<int:connection_id>/messages")
def get_chat_messages(connection_id):
    user_id = session.get("uid")
    if not user_id:
        return {"error": "Not authenticated"}, 401
    
    with get_cursor(commit=True) as cur:
        # Verify user is part of this connection
        cur.execute("""
            SELECT id FROM user_connection 
            WHERE id = %s AND (user1_id = %s OR user2_id = %s)
        """, (connection_id, user_id, user_id))
        
        if not cur.fetchone():
            return {"error": "Access denied"}, 403
        
        # Get latest messages
        cur.execute("""
            SELECT 
                cm.id,
                cm.message,
                cm.sent_at,
                cm.sender_id,
                sender.nickname as sender_nickname,
                cm.sender_id = %s as is_me
            FROM chat_message cm
            JOIN app_user sender ON cm.sender_id = sender.id
            WHERE cm.connection_id = %s
            ORDER BY cm.sent_at ASC
        """, (user_id, connection_id))
        messages = cur.fetchall()
        
        # Mark messages as read
        cur.execute("""
            UPDATE chat_message 
            SET read_at = now() 
            WHERE connection_id = %s 
            AND sender_id != %s 
            AND read_at IS NULL
        """, (connection_id, user_id))
        
        # Generate HTML for messages
        messages_html = ""
        for msg in messages:
            align = "text-align: right;" if msg['is_me'] else ""
            bg_color = "var(--acc)" if msg['is_me'] else "#2a2f3d"
            text_color = "#0b1220" if msg['is_me'] else "var(--txt)"
            radius = "border-bottom-right-radius: 4px;" if msg['is_me'] else "border-bottom-left-radius: 4px;"
            
            messages_html += f"""
            <div style="margin-bottom: 1rem; {align}">
                <div style="display: inline-block; max-width: 70%; padding: 0.5rem 1rem; border-radius: 12px; 
                           background: {bg_color}; color: {text_color}; {radius}">
                    <p style="margin: 0;">{msg['message']}</p>
                    <small style="opacity: 0.8; font-size: 0.8rem;">
                        {msg['sent_at'].strftime('%H:%M')}
                    </small>
                </div>
            </div>
            """
        
        if not messages:
            messages_html = """
            <div style="text-align: center; color: var(--muted); margin-top: 2rem;">
                <p>🎉 Ihr seid jetzt verbunden!</p>
                <p>Startet euer Gespräch mit einer Nachricht...</p>
            </div>
            """
    
    return {"messages": [dict(msg) for msg in messages], "html": messages_html}

@app.post("/chat/<int:connection_id>/send")
def send_message(connection_id):
    user_id = session.get("uid")
    if not user_id:
        return redirect(url_for("index"))
    
    message = request.form.get("message", "").strip()
    if not message:
        return redirect(url_for("chat_view", connection_id=connection_id))
    
    with get_cursor(commit=True) as cur:
        # Verify user is part of this connection
        cur.execute("""
            SELECT id FROM user_connection 
            WHERE id = %s AND (user1_id = %s OR user2_id = %s)
        """, (connection_id, user_id, user_id))
        
        if not cur.fetchone():
            return redirect(url_for("connections"))
        
        # Insert message
        cur.execute("""
            INSERT INTO chat_message (connection_id, sender_id, message)
            VALUES (%s, %s, %s)
        """, (connection_id, user_id, message))
        
        # Update last activity
        cur.execute("""
            UPDATE user_connection 
            SET last_activity = now() 
            WHERE id = %s
        """, (connection_id,))
    
    return redirect(url_for("chat_view", connection_id=connection_id))

@app.post("/reveal/<uuid:sid>")
def reveal(sid):
    user_id = session.get("uid")
    vote = request.form.get("vote","no")
    
    with get_cursor(commit=True) as cur:
        # Record the vote
        cur.execute("""
            INSERT INTO reveal_decision (session_id, user_id, vote)
            VALUES (%s, %s, %s)
            ON CONFLICT (session_id, user_id) DO UPDATE SET vote=EXCLUDED.vote, decided_at=now()
        """, (str(sid), user_id, vote))
        
        # Check if both users voted yes
        cur.execute("""
            SELECT COUNT(*) AS yescnt, 
                   array_agg(user_id) as voters
            FROM reveal_decision 
            WHERE session_id=%s AND vote='yes'
        """, (str(sid),))
        result = cur.fetchone()
        yescnt = result["yescnt"]
        voters = result["voters"] or []
        
        # If both voted yes, create connection
        if yescnt == 2:
            # Get all participants in this session
            cur.execute("""
                SELECT user_id FROM session_participant 
                WHERE session_id = %s
                ORDER BY user_id
            """, (str(sid),))
            participants = [row["user_id"] for row in cur.fetchall()]
            
            if len(participants) == 2:
                user1_id, user2_id = sorted(participants)  # Ensure consistent ordering
                
                # Create connection (ignore if already exists)
                try:
                    cur.execute("""
                        INSERT INTO user_connection (user1_id, user2_id, session_id, chat_active)
                        VALUES (%s, %s, %s, TRUE)
                        ON CONFLICT (user1_id, user2_id, session_id) DO UPDATE SET chat_active = TRUE
                        RETURNING id
                    """, (user1_id, user2_id, str(sid)))
                    
                    connection_result = cur.fetchone()
                    connection_id = connection_result['id']
                    
                    print(f"💫 Connection created! Users {user1_id[:8]} ↔ {user2_id[:8]} → Chat {connection_id}")
                    
                    # Mark session as ended
                    cur.execute("""
                        UPDATE conversation_session 
                        SET status = 'ended', ended_at = now()
                        WHERE id = %s
                    """, (str(sid),))
                    
                    # Store connection info temporarily in a global dict (simple solution)
                    # In production, you'd use Redis or similar
                    if not hasattr(app, 'pending_connections'):
                        app.pending_connections = {}
                    
                    # Store for both users
                    for participant_id in participants:
                        app.pending_connections[participant_id] = connection_id
                    
                    print(f"🔄 Stored connection {connection_id} for users {participants}")
                    
                except Exception as e:
                    print(f"Error creating connection: {e}")
    
    # Redirect based on vote result
    if vote == "yes" and yescnt == 2:
        # Check if we have a pending connection for this user
        if hasattr(app, 'pending_connections'):
            connection_id = app.pending_connections.get(user_id)
            if connection_id:
                # Clean up the pending connection
                app.pending_connections.pop(user_id, None)
                print(f"🚀 Redirecting user {user_id[:8]} to chat {connection_id}")
                return redirect(url_for("chat_view", connection_id=connection_id))
        
        # Fallback to connections page
        return redirect(url_for("connections"))
    else:
        return redirect(url_for("index"))

# --------- WebSocket Signaling (MVP) ---------
@sock.route("/ws/signal/<room>")
def signal(ws, room):
    if room not in signal_rooms:
        signal_rooms[room] = []
    clients = signal_rooms[room]
    clients.append(ws)
    try:
        while True:
            data = ws.receive()
            if data is None:
                break
            # an alle anderen im Raum weiterleiten
            for c in clients:
                if c is not ws:
                    try:
                        c.send(data)
                    except Exception:
                        pass
    finally:
        clients.remove(ws)
        if not clients:
            del signal_rooms[room]

if __name__ == "__main__":
    # Check if SSL certificates exist
    import os.path
    cert_file = 'deeptalk.crt'
    key_file = 'deeptalk.key'
    
    if os.path.exists(cert_file) and os.path.exists(key_file):
        print("🔒 Starting with HTTPS support")
        app.run(host='0.0.0.0', port=5000, debug=True, ssl_context=(cert_file, key_file))
    else:
        print("⚠️  Starting with HTTP only (SSL certificates not found)")
        app.run(host='0.0.0.0', port=5000, debug=True)
