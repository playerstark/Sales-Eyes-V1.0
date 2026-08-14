# Material Upload Feature - Files Created and Modified

## New Files Created

### Backend Models
- **`backend/app/models/materials.py`** - CompanyMaterial model for storing uploaded files

### Backend Services
- **`backend/app/services/painpoint_service.py`** - Service for extracting and synthesizing pain points from materials

### Backend Routes
- **`backend/app/routes/materials.py`** - API endpoints for file upload and material management

### Database Migrations
- **`database/003_add_materials_support.sql`** - SQL migration to add new tables and columns

### Frontend Components
- **`frontend/components/MaterialUpload.tsx`** - Component for uploading company materials
- **`frontend/components/MaterialsList.tsx`** - Component for displaying uploaded materials
- **`frontend/components/PainPointsDisplay.tsx`** - Component for displaying pain points with sources

### Documentation
- **`MATERIAL_UPLOAD_FEATURE.md`** - Comprehensive feature documentation
- **`FILES_CREATED_AND_MODIFIED.md`** - This file

## Modified Files

### Backend
1. **`backend/app/main.py`**
   - Added import: `from app.routes import materials`
   - Added router: `app.include_router(materials.router)`

2. **`backend/app/models/__init__.py`**
   - Added import: `from app.models.materials import CompanyMaterial`
   - Added to exports: `CompanyMaterial`

3. **`backend/app/models/schemas.py`**
   - Added `CompanyMaterialOut` schema
   - Added `CompanyMaterialCreate` schema
   - Added `PainPointOut` schema
   - Updated `FindingOut` schema with new fields: `source_type`, `source_reference`, `details`

4. **`backend/app/models/research.py`**
   - Enhanced `Finding` model with:
     - `source_type` field (VARCHAR)
     - `source_reference` field (VARCHAR)
     - `details` field (JSONB)

5. **`backend/app/core/config.py`**
   - Added import: `import os` and `from pathlib import Path`
   - Added `BASE_DIR` setting for file storage location

6. **`backend/app/services/deepseek_service.py`**
   - Added method: `extract_pain_points()` - Extract pain points from material
   - Added method: `synthesize_pain_points()` - Synthesize pain points from research

7. **`backend/app/routes/research.py`**
   - Added import: `from app.models.materials import CompanyMaterial`
   - Added import: `from app.services.painpoint_service import PainPointService`
   - Added endpoint: `POST /api/research/sessions/{session_id}/analyze-materials`
   - Added endpoint: `POST /api/research/sessions/{session_id}/generate-pain-points`

### Frontend
1. **`frontend/lib/api.ts`**
   - Added method: `uploadMaterial()` - Upload file to server
   - Added method: `getMaterials()` - Get materials for session
   - Added method: `deleteMaterial()` - Delete a material
   - Added method: `analyzeMaterials()` - Analyze uploaded materials
   - Added method: `generatePainPoints()` - Generate pain points from research

2. **`frontend/app/research/[sessionId]/page.tsx`**
   - Added imports for new components: `MaterialUpload`, `MaterialsList`, `PainPointsDisplay`
   - Added state: `refreshMaterials` for handling material updates
   - Added MaterialUpload section to render
   - Added MaterialsList section to render
   - Added PainPointsDisplay section to render

## Summary of Changes

### Backend Architecture
- **File Storage**: Files uploaded to `{BASE_DIR}/uploads/` with UUID naming
- **Database**: New `company_materials` table with relationships to users and sessions
- **Services**: New `PainPointService` handles pain point extraction and synthesis
- **API**: 4 new endpoints for materials and 2 for pain point analysis

### Frontend Architecture
- **Components**: 3 new reusable components for upload, listing, and display
- **API Integration**: Updated API client with material and pain point methods
- **UX**: Integrated material upload into research flow before findings display

### Data Model Enhancements
- Pain points now track their source (internet, uploaded material, or research analysis)
- Findings include detailed metadata about pain points
- Materials linked to sessions with user ownership

## API Endpoints Reference

### Materials Endpoints
```
POST /api/materials/upload
  - Upload a new material
  - Body: FormData with file, material_type, name, session_id, optional description

GET /api/materials/session/{session_id}
  - List all materials for a session
  - Response: { materials: [ CompanyMaterialOut ] }

GET /api/materials/{material_id}
  - Get specific material details
  - Response: CompanyMaterialOut

DELETE /api/materials/{material_id}
  - Delete a material
  - Response: { status: "deleted" }
```

### Pain Point Endpoints
```
POST /api/research/sessions/{session_id}/analyze-materials
  - Extract pain points from uploaded materials
  - Response: { materials_analyzed, pain_points_extracted, findings }

POST /api/research/sessions/{session_id}/generate-pain-points
  - Synthesize pain points from all research findings
  - Response: { pain_points_generated, findings }
```

## Database Schema Changes

### New Table: company_materials
```sql
- id (UUID) - Primary key
- owner_id (UUID) - Foreign key to users
- session_id (UUID) - Foreign key to research_sessions
- material_type (VARCHAR) - Type of material
- name (VARCHAR) - Display name
- file_path (VARCHAR) - Storage path
- file_size (INTEGER) - Bytes
- mime_type (VARCHAR) - Content type
- content_text (TEXT) - Extracted content
- description (TEXT) - Optional user notes
- created_at, updated_at (TIMESTAMP)
```

### Modified Table: findings
```sql
Added columns:
- source_type (VARCHAR) - How the finding was discovered
- source_reference (VARCHAR) - Link to source
- details (JSONB) - Additional metadata
```

## Installation Steps

1. **Database Migration**
   ```bash
   # Run the SQL migration
   psql -U user -d database < database/003_add_materials_support.sql
   ```

2. **Backend Setup**
   - All new models and routes are already integrated into main.py
   - Ensure `DEEPSEEK_API_KEY` is set in .env for pain point extraction

3. **Frontend Setup**
   - New components are ready to use
   - Research page already imports and uses them
   - No additional npm packages required

4. **Testing**
   ```bash
   # Test file upload
   curl -X POST http://localhost:8000/api/materials/upload \
     -H "Authorization: Bearer {token}" \
     -F "file=@brochure.pdf" \
     -F "material_type=brochure" \
     -F "name=Q4 Brochure" \
     -F "session_id={session_id}"
   ```

## Performance Notes

- File upload size limited to 50MB
- Text extraction limited to first 5000 chars for API efficiency
- Indexed queries on owner_id, session_id, source_type
- Lazy loading of materials lists
- Efficient pain point filtering by source type

## Security Features

- User ownership verification on all material access
- Session ownership cascade delete
- Safe file path handling with UUID
- MIME type and extension validation
- No code execution from uploaded files
