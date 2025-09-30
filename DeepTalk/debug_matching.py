#!/usr/bin/env python3
"""Debug the matching issue."""

import sys
sys.path.insert(0, '/home/tim/DeepTalk')

from db import get_cursor

def debug_matching_state():
    """Check the current state of users and queue."""
    
    try:
        with get_cursor() as cur:
            # Check all users
            cur.execute("SELECT id, email, onboarding_done, created_at FROM app_user ORDER BY created_at DESC;")
            users = cur.fetchall()
            print(f"📊 Total users in database: {len(users)}")
            for user in users:
                print(f"  User: {user['id']} | Email: {user['email']} | Created: {user['created_at']}")
            
            print()
            
            # Check match queue
            cur.execute("SELECT user_id, enqueued_at, mood, style, lang FROM match_queue ORDER BY enqueued_at ASC;")
            queue = cur.fetchall()
            print(f"🎯 Users currently in match queue: {len(queue)}")
            for entry in queue:
                print(f"  Queue: {entry['user_id']} | Enqueued: {entry['enqueued_at']} | Mood: {entry['mood']}")
            
            print()
            
            # Check active sessions
            cur.execute("SELECT id, status, created_at, ice_room_key FROM conversation_session ORDER BY created_at DESC LIMIT 5;")
            sessions = cur.fetchall()
            print(f"💬 Recent conversation sessions: {len(sessions)}")
            for sess in sessions:
                print(f"  Session: {sess['id']} | Status: {sess['status']} | Room: {sess['ice_room_key']}")
            
            print()
            
            # Check session participants
            cur.execute("""
                SELECT sp.session_id, sp.user_id, sp.joined_at, cs.status 
                FROM session_participant sp 
                JOIN conversation_session cs ON sp.session_id = cs.id 
                ORDER BY sp.joined_at DESC LIMIT 10;
            """)
            participants = cur.fetchall()
            print(f"👥 Recent session participants: {len(participants)}")
            for part in participants:
                print(f"  Participant: {part['user_id']} | Session: {part['session_id']} | Status: {part['status']}")
            
        return True
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        return False

def clear_stuck_state():
    """Clear any stuck users or sessions."""
    
    try:
        with get_cursor(commit=True) as cur:
            # Clear match queue
            cur.execute("DELETE FROM match_queue;")
            print("✅ Cleared match queue")
            
            # Clear recent sessions (keep data but mark as ended)
            cur.execute("UPDATE conversation_session SET status = 'ended' WHERE status != 'ended';")
            print("✅ Ended active sessions")
            
        return True
        
    except Exception as e:
        print(f"❌ Clear failed: {e}")
        return False

if __name__ == "__main__":
    print("=== DeepTalk Matching Debug ===")
    debug_matching_state()
    
    print("\n" + "="*50)
    print("Do you want to clear stuck state? (y/N): ", end="")
    
    # For automated clearing in this context, let's clear it
    print("y (auto)")
    clear_stuck_state()
    
    print("\n=== State after clearing ===")
    debug_matching_state()