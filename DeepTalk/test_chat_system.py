#!/usr/bin/env python3
"""Test and fix the chat system."""

import sys
sys.path.insert(0, '/home/tim/DeepTalk')

from db import get_cursor

def test_chat_system():
    """Test if the chat system is working."""
    
    print("🧪 Testing Chat System")
    print("=" * 50)
    
    try:
        # Check existing connections
        with get_cursor() as cur:
            cur.execute("""
                SELECT 
                    uc.id,
                    u1.nickname as user1_name,
                    u2.nickname as user2_name,
                    uc.connected_at,
                    uc.chat_active
                FROM user_connection uc
                JOIN app_user u1 ON uc.user1_id = u1.id
                JOIN app_user u2 ON uc.user2_id = u2.id
                ORDER BY uc.connected_at DESC
                LIMIT 5
            """)
            
            connections = cur.fetchall()
            print(f"✅ Found {len(connections)} existing connections:")
            for conn in connections:
                print(f"   Connection {conn['id']}: {conn['user1_name']} ↔ {conn['user2_name']} (Active: {conn['chat_active']})")
            
            if connections:
                # Test adding a message to the latest connection
                latest_conn = connections[0]
                conn_id = latest_conn['id']
                
                # Get users of this connection
                cur.execute("""
                    SELECT user1_id, user2_id FROM user_connection WHERE id = %s
                """, (conn_id,))
                users = cur.fetchone()
                
                test_message = "🧪 Test-Nachricht vom System"
                cur.execute("""
                    INSERT INTO chat_message (connection_id, sender_id, message)
                    VALUES (%s, %s, %s)
                """, (conn_id, users['user1_id'], test_message))
                
                print(f"✅ Test message added to connection {conn_id}")
                
                # Check messages
                cur.execute("""
                    SELECT COUNT(*) as count FROM chat_message WHERE connection_id = %s
                """, (conn_id,))
                msg_count = cur.fetchone()['count']
                print(f"✅ Connection {conn_id} has {msg_count} messages")
                
        return True
        
    except Exception as e:
        print(f"❌ Chat system test failed: {e}")
        return False

if __name__ == "__main__":
    test_chat_system()