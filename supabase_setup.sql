-- Supabase SQL Setup for GearShift Bot
-- Run this SQL in your Supabase SQL Editor to create the warnings table

CREATE TABLE IF NOT EXISTS warnings (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    moderator_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create an index on user_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_warnings_user_id ON warnings(user_id);

-- Optional: Add a comment to the table
COMMENT ON TABLE warnings IS 'Stores moderation warnings for GearShift Bot';

