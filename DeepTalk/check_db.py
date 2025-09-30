#!/usr/bin/env python3
"""Check database connection and permissions."""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def check_database():
    """Check if we can connect to the database and what permissions we have."""
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Check if we can connect
        print("✅ Database connection successful!")
        
        # Check current user
        cur.execute("SELECT current_user, session_user;")
        user_info = cur.fetchone()
        print(f"Current user: {user_info[0]}, Session user: {user_info[1]}")
        
        # Check if database exists
        cur.execute("SELECT current_database();")
        db_name = cur.fetchone()[0]
        print(f"Connected to database: {db_name}")
        
        # Check if tables exist
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'app_user';
        """)
        
        table_exists = cur.fetchone()
        if table_exists:
            print("✅ Table 'app_user' already exists!")
        else:
            print("❌ Table 'app_user' does not exist!")
            
        # Check what tables do exist
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        
        tables = cur.fetchall()
        if tables:
            print(f"Existing tables: {[t[0] for t in tables]}")
        else:
            print("No tables found in public schema.")
            
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        
        # Try to create the database if it doesn't exist
        try:
            # Connect to postgres database to create our database
            db_url_parts = DATABASE_URL.split('/')
            postgres_url = '/'.join(db_url_parts[:-1]) + '/postgres'
            
            print(f"Trying to create database using: {postgres_url}")
            conn = psycopg2.connect(postgres_url)
            conn.autocommit = True
            cur = conn.cursor()
            
            # Extract database name from URL
            db_name = db_url_parts[-1]
            
            # Create database
            cur.execute(f'CREATE DATABASE "{db_name}";')
            print(f"✅ Database '{db_name}' created successfully!")
            
            cur.close()
            conn.close()
            
            # Now try to initialize the schema
            return True
            
        except Exception as create_error:
            print(f"❌ Failed to create database: {create_error}")
            return False

if __name__ == "__main__":
    check_database()