# Quick Start: Material Upload & Pain Points

## For Users

### 1. Upload Company Materials
After creating a research session, you'll see an "Upload Company Materials" section:

- **Material Type**: Select from:
  - Company Brochure
  - Sales Script Sample
  - Product Information
  - Custom Material

- **Material Name**: Give it a descriptive name (e.g., "2024 Product Brochure")
- **Description**: Optional context about the material
- **File**: Upload PDF, TXT, DOC, DOCX, XLSX, or XLS (max 50MB)

### 2. View Uploaded Materials
Below the upload form, see all materials uploaded for this research:
- Shows file size, type, and date uploaded
- Delete materials as needed

### 3. Identify Pain Points
The "Identified Pain Points" section shows:
- **Source Icon**: 
  - 🌐 = Found on the internet
  - 📄 = From your uploaded materials
  - 🔍 = From research analysis
  
- **Pain Point Details**:
  - Title and description
  - Source type badge
  - Material type (if from material)
  - Relevance level (High/Medium/Low)
  - Confidence score (0-100%)
  
- **Supporting Information**:
  - Material name it came from
  - Direct links to source articles
  - Related sources and citations
  - Industry context
  - Whether it's a trending issue

### 4. Use in Script Generation
Selected pain points from all sources (materials + research) are used in script generation to:
- Create personalized openers
- Address specific challenges
- Propose targeted solutions

## For Developers

### Installation

1. **Run Database Migration**
```bash
cd database
psql -U salesstalker -d sales_stalker < 003_add_materials_support.sql
```

2. **Backend is Ready**
- All models and routes already integrated
- No additional pip packages needed
- Requires `DEEPSEEK_API_KEY` in .env

3. **Frontend is Ready**
- Components automatically included in research page
- No additional npm packages needed

### Test the Feature

**1. Create a session:**
```bash
curl -X POST http://localhost:8000/api/research/sessions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {token}" \
  -d '{"prospect_input": "VP of Sales at TechCorp"}'
```

**2. Upload a material:**
```bash
curl -X POST http://localhost:8000/api/materials/upload \
  -H "Authorization: Bearer {token}" \
  -F "session_id={session_id}" \
  -F "material_type=brochure" \
  -F "name=Product Brochure" \
  -F "file=@/path/to/brochure.pdf"
```

**3. Analyze materials:**
```bash
curl -X POST http://localhost:8000/api/research/sessions/{session_id}/analyze-materials \
  -H "Authorization: Bearer {token}"
```

**4. Get pain points:**
```bash
curl -X GET http://localhost:8000/api/research/sessions/{session_id}/findings \
  -H "Authorization: Bearer {token}"
```

## Key Features

### Pain Point Extraction
- **From Materials**: Analyzes text content of uploaded files
- **From Research**: Synthesizes internet research findings
- **Source Tracking**: Every pain point shows where it came from

### Pain Point Details Include
- **Confidence Score**: How sure the AI is (0-100%)
- **Relevance**: High/Medium/Low priority
- **Material Source**: Which file it came from
- **Internet Sources**: Links to supporting articles
- **Industry Context**: What industry segment
- **Trend Analysis**: Is this a trending issue?

### Smart Display
- Pain points organized by source type
- Color-coded priority badges
- Direct links to source materials
- Multiple source references
- Responsive design for all devices

## User Workflow

```
1. Start Research
   ↓
2. Enter prospect information
   ↓
3. ← NEW: Upload company materials (optional but recommended)
   ↓
4. ← NEW: View pain points with sources
   ↓
5. Select relevant findings
   ↓
6. Choose sales methodology (SPIN/Challenger/Sandler)
   ↓
7. Generate personalized sales script
```

## Tips for Best Results

### Material Selection
1. **Include Variety**
   - Product/service brochures
   - Your best sales scripts
   - Industry reports
   - Customer case studies
   - Competitive comparisons

2. **Text-Based Formats**
   - TXT, DOC, DOCX work best
   - PDF requires text (not image-only)
   - XLSX useful for pricing/feature tables

3. **Content Quality**
   - Clear language
   - Specific pain points mentioned
   - Real customer feedback
   - Quantifiable results/metrics

### Pain Point Usage
1. **Review All Sources**
   - Internet research findings
   - Materials-based pain points
   - Research agent analysis

2. **Select Strategically**
   - Pick 3-5 most relevant pain points
   - Mix from different sources
   - Include both industry trends and company-specific

3. **Use in Script**
   - Generated script addresses selected pain points
   - Opens with research-backed insights
   - Proposes solutions to specific challenges

## Troubleshooting

### Materials Won't Upload
- Check file size (max 50MB)
- Verify file format is supported
- Ensure auth token is valid

### No Pain Points Showing
- Confirm materials were uploaded
- Check DeepSeek API key is set
- Wait for analysis to complete (30 seconds)
- Refresh page to see latest findings

### Pain Points Missing Sources
- Ensure analysis completed
- Check findings have details populated
- Verify database migration ran

## File Size Guidelines

| Format | Best Practice | Max Size |
|--------|---------------|----------|
| TXT    | <10MB         | 50MB     |
| PDF    | <5MB          | 50MB     |
| DOCX   | <3MB          | 50MB     |
| XLSX   | <2MB          | 50MB     |

## Performance

- Upload: ~1-2 seconds per MB
- Analysis: ~30 seconds for material
- Display: Instant (lazy loaded)
- Pain points: Generated on demand

## Next Steps

1. **Try the Feature**
   - Upload a sales brochure
   - Upload a sample script
   - View the extracted pain points

2. **Review Generated Script**
   - See how materials inform script
   - Check if pain points are addressed
   - Customize as needed

3. **Iterate**
   - Try different materials
   - Experiment with sources
   - Refine for your prospects

## Support

For issues or questions:
1. Check the `MATERIAL_UPLOAD_FEATURE.md` documentation
2. Review `FILES_CREATED_AND_MODIFIED.md` for technical details
3. Check backend logs for API errors
4. Verify database migration completed
