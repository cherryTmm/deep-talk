-- Profile & Connections Schema Update
-- Add profile fields to app_user table

ALTER TABLE app_user 
ADD COLUMN IF NOT EXISTS nickname TEXT,
ADD COLUMN IF NOT EXISTS bio TEXT,
ADD COLUMN IF NOT EXISTS profile_completed BOOLEAN DEFAULT FALSE;

-- Create connections table for mutual reveals
CREATE TABLE IF NOT EXISTS user_connection (
  id BIGSERIAL PRIMARY KEY,
  user1_id UUID NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  user2_id UUID NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  session_id UUID NOT NULL REFERENCES conversation_session(id) ON DELETE CASCADE,
  connected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(user1_id, user2_id, session_id)
);

-- Create index for faster connection lookups
CREATE INDEX IF NOT EXISTS idx_user_connection_user1 ON user_connection(user1_id);
CREATE INDEX IF NOT EXISTS idx_user_connection_user2 ON user_connection(user2_id);

-- Add some sample nicknames for existing users (optional)
UPDATE app_user 
SET nickname = 'Anonym_' || SUBSTRING(id::text, 1, 8), 
    bio = 'Noch kein Profil erstellt...',
    profile_completed = FALSE
WHERE nickname IS NULL;