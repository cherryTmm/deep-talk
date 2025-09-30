#!/usr/bin/env python3
"""Test the profile and connections system."""

import sys
sys.path.insert(0, '/home/tim/DeepTalk')

from db import get_cursor
import uuid

def test_profile_system():
    """Test profile creation and connections."""
    
    print("🧪 Testing Profile & Connections System")
    print("=" * 50)
    
    try:
        # Test 1: Check schema updates
        with get_cursor() as cur:
            cur.execute("SELECT nickname, bio, profile_completed FROM app_user LIMIT 1")
            user = cur.fetchone()
            print("✅ Profile columns exist:", bool(user))
            
            cur.execute("SELECT COUNT(*) as count FROM user_connection")
            conn_count = cur.fetchone()['count']
            print(f"✅ Connections table exists with {conn_count} connections")
        
        # Test 2: Create test users with profiles
        with get_cursor(commit=True) as cur:
            # Create two test users
            cur.execute("""
                INSERT INTO app_user (nickname, bio, profile_completed, onboarding_done)
                VALUES ('TestUser1', 'Ich liebe tiefe Gespräche!', TRUE, TRUE)
                RETURNING id
            """)
            user1_id = cur.fetchone()['id']
            
            cur.execute("""
                INSERT INTO app_user (nickname, bio, profile_completed, onboarding_done)
                VALUES ('TestUser2', 'Philosophie und Kaffee sind mein Leben.', TRUE, TRUE)
                RETURNING id
            """)
            user2_id = cur.fetchone()['id']
            
            print(f"✅ Created test users: {user1_id[:8]} and {user2_id[:8]}")
            
            # Create a test session
            session_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO conversation_session (id, status, ice_room_key)
                VALUES (%s, 'ended', 'test_room')
            """, (session_id,))
            
            # Add participants
            cur.execute("""
                INSERT INTO session_participant (session_id, user_id, joined_at)
                VALUES (%s, %s, now()), (%s, %s, now())
            """, (session_id, user1_id, session_id, user2_id))
            
            # Add reveal votes
            cur.execute("""
                INSERT INTO reveal_decision (session_id, user_id, vote)
                VALUES (%s, %s, 'yes'), (%s, %s, 'yes')
            """, (session_id, user1_id, session_id, user2_id))
            
            # Create connection
            user1_sorted, user2_sorted = sorted([user1_id, user2_id])
            cur.execute("""
                INSERT INTO user_connection (user1_id, user2_id, session_id)
                VALUES (%s, %s, %s)
            """, (user1_sorted, user2_sorted, session_id))
            
            print("✅ Created test connection between users")
            
        # Test 3: Query connections
        with get_cursor() as cur:
            cur.execute("""
                SELECT 
                    uc.connected_at,
                    other_user.nickname,
                    other_user.bio
                FROM user_connection uc
                JOIN app_user other_user ON (
                    CASE 
                        WHEN uc.user1_id = %s THEN uc.user2_id = other_user.id
                        ELSE uc.user1_id = other_user.id
                    END
                )
                WHERE uc.user1_id = %s OR uc.user2_id = %s
            """, (user1_id, user1_id, user1_id))
            
            connections = cur.fetchall()
            print(f"✅ User1 has {len(connections)} connection(s)")
            for conn in connections:
                print(f"   → Connected to: {conn['nickname']} - {conn['bio']}")
        
        print("\n🎉 All tests passed! Profile & Connections system is working!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    test_profile_system()