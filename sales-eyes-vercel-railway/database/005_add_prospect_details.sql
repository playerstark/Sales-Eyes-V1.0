-- Add structured prospect fields so the app can target web/news search and
-- personalize generated scripts by name, rather than only having the raw
-- freeform prospect_input blob.
ALTER TABLE research_sessions ADD COLUMN IF NOT EXISTS prospect_name VARCHAR(255);
ALTER TABLE research_sessions ADD COLUMN IF NOT EXISTS prospect_company VARCHAR(255);
ALTER TABLE research_sessions ADD COLUMN IF NOT EXISTS prospect_title VARCHAR(255);
