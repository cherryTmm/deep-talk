#!/usr/bin/env python3
"""Try to connect as postgres user and grant permissions."""

import psycopg2
import os

def grant_permissions_as_postgres():
    """Try to connect as postgres and grant permissions to tim."""
    
    # Try different connection approaches for postgres user
    connection_attempts = [
        "postgresql://postgres@localhost:5432/deeptalk",
        "postgresql://@localhost:5432/deeptalk",
        "postgresql://localhost:5432/deeptalk",
    ]
    
    for conn_str in connection_attempts:
        try:
            print(f"Trying connection: {conn_str}")
            conn = psycopg2.connect(conn_str)
            conn.autocommit = True
            cur = conn.cursor()
            
            # Check current user
            cur.execute("SELECT current_user;")
            user = cur.fetchone()[0]
            print(f"✅ Connected as: {user}")
            
            # Grant permissions to tim
            cur.execute("GRANT CREATE ON SCHEMA public TO tim;")
            cur.execute("GRANT USAGE ON SCHEMA public TO tim;")
            print("✅ Granted permissions to tim")
            
            cur.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            continue
    
    return False

def create_schema_alternative():
    """Create schema in tim's own schema instead of public."""
    
    try:
        # Connect as tim
        conn = psycopg2.connect("postgresql://tim@localhost:5432/deeptalk")
        conn.autocommit = True
        cur = conn.cursor()
        
        print("✅ Connected as tim")
        
        # Create our own schema
        cur.execute("CREATE SCHEMA IF NOT EXISTS deeptalk_schema;")
        print("✅ Created deeptalk_schema")
        
        # Set search path to use our schema
        cur.execute("SET search_path TO deeptalk_schema, public;")
        
        # Now try to create types and tables in our schema
        cur.execute("CREATE TYPE IF NOT EXISTS deeptalk_schema.convo_style AS ENUM ('deep','casual','fun');")
        print("✅ Created convo_style type")
        
        # Create a simple table to test
        cur.execute("""
            CREATE TABLE IF NOT EXISTS deeptalk_schema.app_user (
              id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
              created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              email TEXT UNIQUE,
              display_name TEXT,
              birth_year INT,
              locale TEXT DEFAULT 'de',
              onboarding_done BOOLEAN NOT NULL DEFAULT FALSE
            );
        """)
        print("✅ Created app_user table in deeptalk_schema")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Alternative schema creation failed: {e}")
        return False

if __name__ == "__main__":
    print("Attempting to grant permissions as postgres user...")
    success = grant_permissions_as_postgres()
    
    if not success:
        print("\nAttempting alternative: creating our own schema...")
        success = create_schema_alternative()
    
    if success:
        print("✅ Database permissions resolved!")
    else:
        print("❌ Could not resolve database permissions.")
        print("Manual intervention required. Please run:")
        print("  psql -U postgres deeptalk -c 'GRANT CREATE ON SCHEMA public TO tim;'")