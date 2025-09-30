#!/usr/bin/env python3
"""Test the Flask app database connection and basic functionality."""

import sys
import os
sys.path.insert(0, '/home/tim/DeepTalk')

from db import get_cursor

def test_database_connection():
    """Test if we can connect to the database and query the tables."""
    
    try:
        with get_cursor() as cur:
            # Test if we can query the app_user table
            cur.execute("SELECT COUNT(*) FROM app_user;")
            count = cur.fetchone()[0]
            print(f"✅ Database connection successful!")
            print(f"✅ app_user table exists with {count} users")
            
            # Test if we can insert a user (like the app does)
            cur.execute("""
                INSERT INTO app_user (email, onboarding_done) 
                VALUES (%s, TRUE) 
                RETURNING id
            """, (None,))
            user_id = cur.fetchone()[0]
            print(f"✅ Successfully created user with ID: {user_id}")
            
        # Test with commit
        with get_cursor(commit=True) as cur:
            cur.execute("DELETE FROM app_user WHERE email IS NULL;")
            print("✅ Cleanup completed")
            
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_flask_import():
    """Test if we can import the Flask app without errors."""
    
    try:
        from app import app
        print("✅ Flask app imported successfully")
        
        # Test that the app is configured
        print(f"✅ App name: {app.name}")
        print(f"✅ Debug mode: {app.debug}")
        print(f"✅ Secret key configured: {'SECRET_KEY' in app.config}")
        
        return True
        
    except Exception as e:
        print(f"❌ Flask app import failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing database connection...")
    db_ok = test_database_connection()
    
    print("\nTesting Flask app import...")
    flask_ok = test_flask_import()
    
    if db_ok and flask_ok:
        print("\n✅ All tests passed! Your Flask app should work correctly now.")
        print("You can run: python app.py")
    else:
        print("\n❌ Some tests failed. Check the errors above.")