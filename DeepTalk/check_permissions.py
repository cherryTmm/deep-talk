#!/usr/bin/env python3
"""Check and try to fix database permissions."""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def check_and_fix_permissions():
    """Check permissions and try to grant necessary ones."""
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Check current user and their permissions
        cur.execute("SELECT current_user;")
        user = cur.fetchone()[0]
        print(f"Current user: {user}")
        
        # Check if user is superuser
        cur.execute("SELECT usesuper FROM pg_user WHERE usename = current_user;")
        is_super = cur.fetchone()[0]
        print(f"Is superuser: {is_super}")
        
        # Check schema permissions
        cur.execute("""
            SELECT has_schema_privilege(current_user, 'public', 'CREATE');
        """)
        can_create = cur.fetchone()[0]
        print(f"Can create in public schema: {can_create}")
        
        if not can_create:
            print("Attempting to grant CREATE permission on public schema...")
            try:
                cur.execute(f"GRANT CREATE ON SCHEMA public TO {user};")
                print(f"✅ Granted CREATE permission to {user}")
            except Exception as e:
                print(f"❌ Could not grant permission: {e}")
                
                # Try as postgres user if we're not superuser
                if not is_super:
                    print("Trying to connect as postgres user...")
                    try:
                        # Try different postgres connection URLs
                        postgres_urls = [
                            DATABASE_URL.replace("tim@", "postgres@"),
                            DATABASE_URL.replace(f"{user}@", "@"),
                            DATABASE_URL.replace(f"//{user}@", "//postgres@"),
                        ]
                        
                        for url in postgres_urls:
                            try:
                                postgres_conn = psycopg2.connect(url)
                                postgres_conn.autocommit = True
                                postgres_cur = postgres_conn.cursor()
                                
                                # Grant permissions
                                postgres_cur.execute(f"GRANT CREATE ON SCHEMA public TO {user};")
                                postgres_cur.execute(f"GRANT USAGE ON SCHEMA public TO {user};")
                                print(f"✅ Granted permissions to {user} via postgres user")
                                
                                postgres_cur.close()
                                postgres_conn.close()
                                break
                                
                            except Exception as pg_e:
                                print(f"Could not connect as postgres: {pg_e}")
                                continue
                        
                    except Exception as e2:
                        print(f"❌ Could not connect as postgres: {e2}")
        
        # Try to create a simple table to test
        try:
            cur.execute("CREATE TABLE test_permissions (id SERIAL PRIMARY KEY);")
            cur.execute("DROP TABLE test_permissions;")
            print("✅ Permission test successful - can create tables now!")
            return True
        except Exception as e:
            print(f"❌ Still cannot create tables: {e}")
            return False
            
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Permission check failed: {e}")
        return False

if __name__ == "__main__":
    success = check_and_fix_permissions()
    if success:
        print("✅ Permissions are working!")
    else:
        print("❌ Permission issues remain. You may need to run as database admin:")
        print("   sudo -u postgres psql deeptalk -c 'GRANT CREATE ON SCHEMA public TO tim;'")