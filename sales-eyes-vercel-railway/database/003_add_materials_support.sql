-- Add new fields to findings table for pain point source tracking
ALTER TABLE findings ADD COLUMN IF NOT EXISTS source_type VARCHAR(50);
ALTER TABLE findings ADD COLUMN IF NOT EXISTS source_reference VARCHAR(512);
ALTER TABLE findings ADD COLUMN IF NOT EXISTS details JSONB;

-- Create company_materials table for storing uploaded files
CREATE TABLE IF NOT EXISTS company_materials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    material_type VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    file_size INTEGER NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    content_text TEXT,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_company_materials_owner_id ON company_materials(owner_id);
CREATE INDEX IF NOT EXISTS idx_company_materials_session_id ON company_materials(session_id);
CREATE INDEX IF NOT EXISTS idx_findings_source_type ON findings(source_type);
CREATE INDEX IF NOT EXISTS idx_findings_source_reference ON findings(source_reference);
