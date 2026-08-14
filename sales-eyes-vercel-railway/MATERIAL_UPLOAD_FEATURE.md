# Material Upload & Pain Points Feature

## Overview
Added comprehensive file upload functionality for company materials (brochures, sales scripts, product information) with automatic pain point extraction and source tracking.

## Features

### 1. File Upload
- **Supported Materials**: Brochures, Sales Scripts, Product Information, Custom Materials
- **Supported Formats**: PDF, TXT, DOC, DOCX, XLSX, XLS
- **Max File Size**: 50MB
- **Auto-extraction**: Text content is extracted and stored for analysis
- **User Descriptions**: Optional context for each uploaded material

### 2. Pain Points Display with Sources
Pain points now show:
- **Source Type**: Where the finding came from (Internet, Uploaded Material, Research Agent)
- **Source Reference**: Links to articles or material IDs
- **Material Reference**: Shows which uploaded material a pain point came from
- **Confidence Score**: How confident the AI is about this pain point
- **Priority Level**: High/Medium/Low relevance
- **Supporting Sources**: Additional references and citations
- **Industry Context**: What industry segment this applies to
- **Trend Analysis**: Whether this is a trending issue

## Backend Implementation

### Database Models

**CompanyMaterial** (`backend/app/models/materials.py`)
```python
- id: UUID (primary key)
- owner_id: UUID (user ownership)
- session_id: UUID (research session)
- material_type: str (brochure|sales_script|product_info|custom)
- name: str (display name)
- file_path: str (local storage path)
- file_size: int (bytes)
- mime_type: str
- content_text: str (extracted text)
- description: str (optional user notes)
- created_at/updated_at: DateTime
```

**Finding** (Enhanced)
```python
# New fields added:
- source_type: str (internet|uploaded_material|research_agent)
- source_reference: str (URL or material ID)
- details: dict (JSONB with additional metadata)
```

### API Endpoints

**Materials Management**
- `POST /api/materials/upload` - Upload a new material
- `GET /api/materials/session/{session_id}` - List materials for session
- `GET /api/materials/{material_id}` - Get specific material
- `DELETE /api/materials/{material_id}` - Delete material

**Pain Point Analysis**
- `POST /api/research/sessions/{session_id}/analyze-materials` - Extract pain points from uploaded materials
- `POST /api/research/sessions/{session_id}/generate-pain-points` - Synthesize pain points from all sources

### Services

**PainPointService** (`backend/app/services/painpoint_service.py`)
- `extract_pain_points_from_material()` - Analyze uploaded content
- `extract_pain_points_from_research()` - Synthesize from research findings

**DeepSeekService** (Enhanced)
- `extract_pain_points()` - Extract pain points from material content
- `synthesize_pain_points()` - Combine findings into pain points with sources

## Frontend Implementation

### Components

**MaterialUpload** (`frontend/components/MaterialUpload.tsx`)
- File upload form with type selection
- Name and description fields
- Drag-and-drop ready
- Validation and error handling
- Upload progress feedback

**MaterialsList** (`frontend/components/MaterialsList.tsx`)
- Displays all uploaded materials for session
- Shows file size and type
- Delete button for each material
- Date created information
- Icon indicators for material type

**PainPointsDisplay** (`frontend/components/PainPointsDisplay.tsx`)
- Shows all identified pain points
- Displays source type with icons:
  - 🌐 Internet Research
  - 📄 Uploaded Material
  - 🔍 Research Analysis
- Source links and references
- Confidence scores
- Priority badges (High/Medium/Low)
- Material references
- Supporting sources list
- Industry context

### API Integration

Updated `frontend/lib/api.ts` with:
```typescript
- uploadMaterial(sessionId, file, materialType, name, description)
- getMaterials(sessionId)
- deleteMaterial(materialId)
- analyzeMaterials(sessionId)
- generatePainPoints(sessionId)
```

### Research Page Integration
Modified `frontend/app/research/[sessionId]/page.tsx` to include:
1. MaterialUpload component at top
2. MaterialsList showing uploaded files
3. PainPointsDisplay showing identified pain points with sources

## User Workflow

1. **Start Research** → Create research session
2. **Generate Plan** → DeepSeek analyzes prospect input
3. **Upload Materials** (NEW) → Upload company documents
4. **View Pain Points** (NEW) → See pain points from:
   - Uploaded materials
   - Internet research
   - Research analysis
5. **Select Findings** → Choose relevant findings
6. **Choose Methodology** → SPIN/Challenger/Sandler
7. **Generate Script** → DeepSeek creates personalized sales script

## Pain Point Extraction

### From Materials
When you upload a material:
1. Text is extracted (if format supports it)
2. DeepSeek analyzes for pain points
3. Pain points are created with:
   - `source_type: "uploaded_material"`
   - Reference to the material ID
   - Extracted title and description
   - Confidence score
   - Relevance (high/medium/low)

### From Research
When analyzing research findings:
1. Synthesizes all research inputs
2. Identifies major pain points
3. Creates findings with:
   - `source_type: "internet"`
   - Links to supporting articles
   - Industry context
   - Trend analysis
   - Multiple source references

## Configuration

### Environment Variables
No new env vars required, uses existing:
- `DEEPSEEK_API_KEY` - For pain point extraction
- File uploads stored in: `{BASE_DIR}/uploads/`

### File Storage
- Location: `{project_root}/uploads/`
- Auto-created if doesn't exist
- Files named by UUID to prevent conflicts
- Original filename preserved in DB

## Security Considerations

1. **File Upload Validation**
   - Size limits (50MB max)
   - MIME type validation
   - File extension checking
   - Async safe file operations

2. **Access Control**
   - All materials owned by user
   - Session ownership verified
   - Cascade delete on session removal

3. **Content Safety**
   - Text extraction limited to first 5000 chars for API
   - No execution of uploaded content
   - Safe path handling with UUID

## Database Migration

Run `database/003_add_materials_support.sql` to:
1. Add columns to findings table (source_type, source_reference, details)
2. Create company_materials table
3. Create indexes for performance

## Performance Optimization

- Indexed queries on: owner_id, session_id, source_type
- Lazy loading of materials list
- Pagination ready for material lists
- Efficient pain point filtering

## Future Enhancements

1. **Supported Formats**
   - PDF text extraction with pdf2image
   - Word document parsing with python-docx
   - Excel sheet analysis
   - Image OCR support

2. **Advanced Analysis**
   - Competitive intelligence extraction
   - Budget/ROI impact quantification
   - Decision-maker pain mapping
   - Timeline/urgency indicators

3. **Collaboration**
   - Material sharing between team members
   - Version history of uploads
   - Comments on pain points
   - Approval workflows

4. **Integration**
   - Direct file upload from cloud storage (Google Drive, Dropbox)
   - Email attachment extraction
   - Website URL content parsing
   - API data source integration

## Troubleshooting

### Upload Fails
- Check file size (max 50MB)
- Verify file format is supported
- Check disk space in uploads directory
- Review API key configuration

### Pain Points Not Generated
- Ensure DeepSeek API key is configured
- Check material content was extracted
- Verify findings exist for synthesis
- Check API rate limits

### Missing Source References
- Ensure material analysis completed before viewing
- Check that findings have details populated
- Verify pain point generation ran

## Testing Checklist

- [ ] Upload various file formats (PDF, TXT, DOCX)
- [ ] Verify files listed correctly
- [ ] Delete materials and confirm removal
- [ ] Generate pain points from materials
- [ ] Check source types display correctly
- [ ] Verify confidence scores show
- [ ] Test priority badges render
- [ ] Confirm material references work
- [ ] Check responsive design on mobile
- [ ] Test with various material sizes
