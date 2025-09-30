#!/usr/bin/env python3
"""Initialize database with better error handling."""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def init_database_step_by_step():
    """Initialize database step by step with better error handling."""
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True  # Important for CREATE statements
        cur = conn.cursor()
        
        print("✅ Connected to database")
        
        # Step 1: Create extensions
        try:
            cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
            print("✅ Created uuid-ossp extension")
        except Exception as e:
            print(f"Extension uuid-ossp: {e}")
            
        try:
            cur.execute('CREATE EXTENSION IF NOT EXISTS citext;')
            print("✅ Created citext extension")
        except Exception as e:
            print(f"Extension citext: {e}")
            
        # Step 2: Create types
        types_sql = [
            "CREATE TYPE convo_style AS ENUM ('deep','casual','fun');",
            "CREATE TYPE session_status AS ENUM ('initiated','connecting','connected','ended','dropped','aborted');",
            "CREATE TYPE reveal_vote AS ENUM ('yes','no');",
            "CREATE TYPE mood_type AS ENUM ('energized','calm','down','curious','lonely','stressed','neutral');"
        ]
        
        for type_sql in types_sql:
            try:
                cur.execute(type_sql)
                print(f"✅ Created type: {type_sql.split()[2]}")
            except psycopg2.errors.DuplicateObject:
                print(f"Type {type_sql.split()[2]} already exists")
            except Exception as e:
                print(f"Error creating type: {e}")
                
        # Step 3: Create tables
        tables_sql = [
            """CREATE TABLE IF NOT EXISTS app_user (
              id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
              created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              email CITEXT UNIQUE,
              display_name TEXT,
              birth_year INT,
              locale TEXT DEFAULT 'de',
              onboarding_done BOOLEAN NOT NULL DEFAULT FALSE
            );""",
            
            """CREATE TABLE IF NOT EXISTS user_preferences (
              user_id UUID PRIMARY KEY REFERENCES app_user(id) ON DELETE CASCADE,
              preferred_style convo_style DEFAULT 'deep',
              preferred_lang TEXT DEFAULT 'de',
              min_age SMALLINT DEFAULT 18,
              max_age SMALLINT DEFAULT 120
            );""",
            
            """CREATE TABLE IF NOT EXISTS match_queue (
              user_id UUID PRIMARY KEY REFERENCES app_user(id) ON DELETE CASCADE,
              enqueued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              mood mood_type DEFAULT 'neutral',
              style convo_style DEFAULT 'deep',
              lang TEXT DEFAULT 'de'
            );""",
            
            """CREATE TABLE IF NOT EXISTS conversation_session (
              id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
              created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              started_at TIMESTAMPTZ,
              ended_at TIMESTAMPTZ,
              status session_status NOT NULL DEFAULT 'initiated',
              lang TEXT,
              style convo_style,
              ice_room_key TEXT UNIQUE
            );""",
            
            """CREATE TABLE IF NOT EXISTS session_participant (
              session_id UUID REFERENCES conversation_session(id) ON DELETE CASCADE,
              user_id UUID REFERENCES app_user(id) ON DELETE CASCADE,
              joined_at TIMESTAMPTZ,
              left_at TIMESTAMPTZ,
              PRIMARY KEY (session_id, user_id)
            );""",
            
            """CREATE TABLE IF NOT EXISTS conversation_card (
              id BIGSERIAL PRIMARY KEY,
              topic TEXT NOT NULL,
              depth SMALLINT NOT NULL DEFAULT 3,
              prompt TEXT NOT NULL
            );""",
            
            """CREATE TABLE IF NOT EXISTS session_card_usage (
              session_id UUID REFERENCES conversation_session(id) ON DELETE CASCADE,
              card_id BIGINT REFERENCES conversation_card(id) ON DELETE SET NULL,
              position SMALLINT NOT NULL,
              PRIMARY KEY (session_id, card_id)
            );""",
            
            """CREATE TABLE IF NOT EXISTS reveal_decision (
              session_id UUID REFERENCES conversation_session(id) ON DELETE CASCADE,
              user_id UUID REFERENCES app_user(id) ON DELETE CASCADE,
              vote reveal_vote NOT NULL,
              decided_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              PRIMARY KEY (session_id, user_id)
            );"""
        ]
        
        for table_sql in tables_sql:
            try:
                cur.execute(table_sql)
                # Extract table name from SQL
                table_name = table_sql.split("TABLE IF NOT EXISTS ")[1].split()[0]
                print(f"✅ Created table: {table_name}")
            except Exception as e:
                print(f"Error creating table: {e}")
                
        # Step 4: Insert initial data
        try:
            cur.execute("""
                INSERT INTO conversation_card(topic, depth, prompt) VALUES
                  ('self',3,'Was würdest du deinem jüngeren Ich sagen?'),
                  ('values',4,'Welche Werte sind dir unverzichtbar?'),
                  ('dreams',3,'Wovon träumst du gerade?')
                ON CONFLICT DO NOTHING;
            """)
            print("✅ Inserted initial conversation cards")
        except Exception as e:
            print(f"Error inserting initial data: {e}")
            
        cur.close()
        conn.close()
        print("✅ Database initialization completed!")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False
        
    return True

if __name__ == "__main__":
    init_database_step_by_step()