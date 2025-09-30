CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS citext;

DO $$ BEGIN
  CREATE TYPE convo_style AS ENUM ('deep','casual','fun');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE session_status AS ENUM ('initiated','connecting','connected','ended','dropped','aborted');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE reveal_vote AS ENUM ('yes','no');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE mood_type AS ENUM ('energized','calm','down','curious','lonely','stressed','neutral');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS app_user (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  email CITEXT UNIQUE,
  display_name TEXT,
  birth_year INT,
  locale TEXT DEFAULT 'de',
  onboarding_done BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS user_preferences (
  user_id UUID PRIMARY KEY REFERENCES app_user(id) ON DELETE CASCADE,
  preferred_style convo_style DEFAULT 'deep',
  preferred_lang TEXT DEFAULT 'de',
  min_age SMALLINT DEFAULT 18,
  max_age SMALLINT DEFAULT 120
);

CREATE TABLE IF NOT EXISTS match_queue (
  user_id UUID PRIMARY KEY REFERENCES app_user(id) ON DELETE CASCADE,
  enqueued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  mood mood_type DEFAULT 'neutral',
  style convo_style DEFAULT 'deep',
  lang TEXT DEFAULT 'de'
);

CREATE TABLE IF NOT EXISTS conversation_session (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  status session_status NOT NULL DEFAULT 'initiated',
  lang TEXT,
  style convo_style,
  ice_room_key TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS session_participant (
  session_id UUID REFERENCES conversation_session(id) ON DELETE CASCADE,
  user_id UUID REFERENCES app_user(id) ON DELETE CASCADE,
  joined_at TIMESTAMPTZ,
  left_at TIMESTAMPTZ,
  PRIMARY KEY (session_id, user_id)
);

CREATE TABLE IF NOT EXISTS conversation_card (
  id BIGSERIAL PRIMARY KEY,
  topic TEXT NOT NULL,
  depth SMALLINT NOT NULL DEFAULT 3,
  prompt TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS session_card_usage (
  session_id UUID REFERENCES conversation_session(id) ON DELETE CASCADE,
  card_id BIGINT REFERENCES conversation_card(id) ON DELETE SET NULL,
  position SMALLINT NOT NULL,
  PRIMARY KEY (session_id, card_id)
);

CREATE TABLE IF NOT EXISTS reveal_decision (
  session_id UUID REFERENCES conversation_session(id) ON DELETE CASCADE,
  user_id UUID REFERENCES app_user(id) ON DELETE CASCADE,
  vote reveal_vote NOT NULL,
  decided_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (session_id, user_id)
);

-- Start-Daten für Cards
INSERT INTO conversation_card(topic, depth, prompt) VALUES
  ('self',3,'Was würdest du deinem jüngeren Ich sagen?'),
  ('values',4,'Welche Werte sind dir unverzichtbar?'),
  ('dreams',3,'Wovon träumst du gerade?')
ON CONFLICT DO NOTHING;
