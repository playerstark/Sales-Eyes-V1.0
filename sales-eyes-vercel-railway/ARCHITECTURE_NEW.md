# Sales Eyes - New Architecture

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    SALES EYES UI                        │
│  (Next.js Frontend - React)                             │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴─────────────┬──────────────┐
        │                          │              │
        ▼                          ▼              ▼
   [HOME PAGE]          [RESEARCH SESSION]   [DASHBOARD]
   - Input prospect     - Display report     - Session list
   - Submit             - Upload material    - Start new
                        - Select method
                        - View script
        │                          │              │
        └──────────────┬───────────┴──────────────┘
                       │
                       ▼
        ┌──────────────────────────────────┐
        │     BACKEND API                   │
        │  (FastAPI + SQLAlchemy)           │
        └───────────┬──────────────────────┘
                    │
        ┌───────────┴─────────────────────┐
        │                                 │
        ▼                                 ▼
    [RESEARCH SERVICE]            [DEEPSEEK SERVICE]
    - Create session              - comprehensive_prospect_research()
    - Parse prospect details      - summarize_research()
    - Generate output             - generate_sales_script()
    - Store findings              - parse_prospect_details()
        │                             │
        └─────────────┬───────────────┘
                      │
                      ▼
           ┌──────────────────────┐
           │  DEEPSEEK API        │
           │  (aicredits.in)      │
           │                      │
           │  Single Call = All   │
           │  Research Data       │
           └──────────────────────┘
                      │
                      ▼
           ┌──────────────────────┐
           │  PostgreSQL          │
           │  (Persistent Data)   │
           │                      │
           │  - Sessions          │
           │  - Findings          │
           │  - Materials         │
           │  - Scripts           │
           └──────────────────────┘
```

## Data Flow - Step by Step

### Step 1: Research Initiation
```
User Input
   ↓
"Arvind Krishna, CEO, IBM"
   ↓
[research_service.py] → parse_prospect_details()
   ├─ Name: Arvind Krishna
   ├─ Title: CEO
   └─ Company: IBM
   ↓
Create ResearchSession in DB
```

### Step 2: Comprehensive Research (THE MAGIC)
```
[research_service.py] → generate_plan()
   ↓
[deepseek_service.py] → comprehensive_prospect_research()
   ↓
[DEEPSEEK API] - Single Powerful Call
   ↓
Returns JSON:
{
  "prospect_name": "Arvind Krishna",
  "professional_background": "...",
  "company_overview": "...",
  "news_and_updates": [
    {
      "title": "IBM Quantum Initiative",
      "date": "2024-12-15",
      "category": "announcement",
      "summary": "...",
      "relevance": "high"
    }
  ],
  "pain_points": [
    {
      "category": "DIGITAL_TRANSFORMATION",
      "issue": "Legacy system modernization",
      "impact": "...",
      "relevance_score": 0.92
    }
  ],
  "sales_hooks": [
    {
      "hook": "AI-driven automation for operational efficiency",
      "based_on": "Efficiency priorities",
      "strength": "high",
      "approach": "CHALLENGER"
    }
  ],
  "strategic_priorities": [
    "Hybrid cloud expansion",
    "AI/ML integration",
    "Cost optimization"
  ]
}
```

### Step 3: Store and Structure
```
[research_service.py] → _create_findings_from_research()
   ↓
For each research element:
  - Create Finding record
  - Set finding_type (news_announcement, pain_point_digital_transformation, etc.)
  - Tag with source_type (research_agent)
  - Store structured data in raw_data JSONB
   ↓
Generate research summary report via DeepSeek
   ↓
Save to ResearchSession.research_summary
```

### Step 4: Display to User
```
[Frontend] → GET /research/{session_id}
   ↓
Return:
  - Research Summary Report (formatted)
  - Individual Findings (categorized)
  - Material Upload Prompt
  - Methodology Selection (next step)
```

### Step 5: Material Upload (Optional)
```
User can:
  ✓ Upload product document (PDF, DOCX, TXT, MD)
  ✓ Skip and use generic value prop
   ↓
Extract text from document
Store in Material model
```

### Step 6: Script Generation
```
User selects: "SPIN" or "Sandler" or "Challenger"
   ↓
[script_service.py] → generate_sales_script()
   ↓
[deepseek_service.py] → generate_sales_script()
   ↓
[DEEPSEEK API] - Specialized Script Call
   Input:
     - Research data (with news, hooks, pain points)
     - Product material
     - Methodology framework
   ↓
   Output:
     [OPENING HOOK - Research-based]
     "Arvind, I noticed IBM announced the quantum initiative last month..."
     
     [SITUATION QUESTIONS - Discovery]
     "How is that impacting your broader AI strategy?"
     
     [PROBLEM QUESTIONS - Pain-focused]
     "What's your biggest challenge in scaling AI across..."
     
     ... etc based on methodology
```

## Key Components

### 1. ResearchSession Model
```python
class ResearchSession(Base):
    id: UUID (Primary Key)
    owner_id: UUID (User)
    prospect_input: str (Raw input from user)
    
    prospect_name: str
    prospect_company: str
    prospect_title: str
    
    research_summary: str (Polished report)
    plan: JSONB (Raw research data from DeepSeek)
    findings: Relationship to Finding
    
    status: str (planning → research_complete → summarized → completed)
    methodology: str (SPIN, Sandler, Challenger)
    generated_output: str (Final sales script)
```

### 2. Finding Model (Structured, Tagged)
```python
class Finding(Base):
    id: UUID
    session_id: UUID
    finding_type: str (news_announcement, pain_point_digital_transformation, sales_hook, etc.)
    
    source_header: str (Display title with tags/dates)
    summary: str (Content)
    source_link: str (Optional URL)
    source_type: str (research_agent)
    source_reference: str (Hook basis, etc.)
    
    raw_data: JSONB (Full original data)
    
    confidence_score: float (0.0-1.0)
    relevancy_score: float (0.0-1.0)
    is_selected: bool
```

### 3. Material Model
```python
class Material(Base):
    id: UUID
    session_id: UUID
    material_type: str (pdf, docx, txt, md)
    file_name: str
    extracted_text: str (Stored for prompt)
```

## API Endpoints

### Research Flow
```
POST /research/sessions
  Input: { owner_id, prospect_input }
  Output: { session_id }

POST /research/{session_id}/plan
  Triggers: comprehensive_prospect_research()
  Output: { plan, findings }

GET /research/{session_id}
  Returns: Full session with research summary

POST /research/{session_id}/materials
  Upload product material

POST /research/{session_id}/script
  Input: { methodology, material_id? }
  Triggers: generate_sales_script()
  Output: { script }
```

## What Makes This Better

### Before (Multiple APIs)
- Web search + News API + LinkedIn API + NLP extraction
- Loose findings with no structure
- Multiple timeout points
- Complex error handling

### After (DeepSeek Single Call)
- One API call with comprehensive prompt
- Structured JSON output with tags/dates
- Faster execution
- Cleaner, maintainable code
- Higher quality research

## Performance

- **Research Time**: 10-15 seconds
- **Database Queries**: 2-3 per session
- **API Calls**: 2 (comprehensive_research + summarize) or 3 (+ script generation)
- **Total Session Time**: 30-45 seconds from prospect input to ready-to-use script

## Scalability

- Zero external dependencies on web scraping APIs
- Single LLM API dependency (easy to swap providers)
- Database scales with users
- No rate limiting issues from multiple APIs

## Security

- No user credentials stored
- No browser automation or scraping
- Clean, structured data flow
- No external data injection risks
- API key secured via environment variables
