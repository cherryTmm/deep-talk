#!/usr/bin/env python3
"""Real-time monitoring of the matching system."""

import sys
import time
sys.path.insert(0, '/home/tim/DeepTalk')

from db import get_cursor
from datetime import datetime

def monitor_matching():
    """Monitor the matching system in real-time."""
    
    print("🔍 DeepTalk Matching Monitor")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    try:
        while True:
            with get_cursor() as cur:
                # Check queue
                cur.execute("SELECT COUNT(*) as count FROM match_queue;")
                queue_count = cur.fetchone()['count']
                
                # Check active sessions
                cur.execute("SELECT COUNT(*) as count FROM conversation_session WHERE status != 'ended';")
                active_sessions = cur.fetchone()['count']
                
                # Get queue details
                cur.execute("SELECT user_id, enqueued_at FROM match_queue ORDER BY enqueued_at;")
                queue_users = cur.fetchall()
                
                # Display status
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"⏱️  {timestamp} | Queue: {queue_count} users | Active Sessions: {active_sessions}", end="")
                
                if queue_users:
                    print(" | Waiting:", end="")
                    for user in queue_users:
                        user_short = str(user['user_id'])[:8]
                        print(f" {user_short}", end="")
                print()
                
                time.sleep(2)
                
    except KeyboardInterrupt:
        print("\n👋 Monitor stopped")

if __name__ == "__main__":
    monitor_matching()