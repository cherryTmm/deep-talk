#!/usr/bin/env python3
"""Initialize the database with the schema."""

import os
from db import get_cursor
from dotenv import load_dotenv

load_dotenv()

def init_database():
    """Read and execute the schema.sql file."""
    
    # Read the schema file
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    # Execute the schema
    try:
        with get_cursor(commit=True) as cur:
            cur.execute(schema_sql)
        print("Database initialized successfully!")
        return True
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False

if __name__ == "__main__":
    success = init_database()
    if success:
        print("✅ Database schema has been applied successfully.")
    else:
        print("❌ Failed to initialize database.")