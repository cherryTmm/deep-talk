-- Chat System Schema Update
-- Add chat messages table for post-reveal conversations

CREATE TABLE IF NOT EXISTS chat_message (
  id BIGSERIAL PRIMARY KEY,
  connection_id BIGINT NOT NULL REFERENCES user_connection(id) ON DELETE CASCADE,
  sender_id UUID NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  message TEXT NOT NULL,
  sent_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  read_at TIMESTAMPTZ
);

-- Create index for faster message lookups
CREATE INDEX IF NOT EXISTS idx_chat_message_connection ON chat_message(connection_id, sent_at);
CREATE INDEX IF NOT EXISTS idx_chat_message_sender ON chat_message(sender_id);

-- Add last_activity to user_connection for chat management
ALTER TABLE user_connection 
ADD COLUMN IF NOT EXISTS last_activity TIMESTAMPTZ DEFAULT now(),
ADD COLUMN IF NOT EXISTS chat_active BOOLEAN DEFAULT TRUE;