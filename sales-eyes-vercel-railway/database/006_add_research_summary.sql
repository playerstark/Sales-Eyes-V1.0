-- Store the synthesized "research report" as one coherent document (what the
-- product spec calls the document that gets sent into the script-generation
-- prompt alongside the uploaded product material), rather than only a
-- scattered list of raw findings.
ALTER TABLE research_sessions ADD COLUMN IF NOT EXISTS research_summary TEXT;
