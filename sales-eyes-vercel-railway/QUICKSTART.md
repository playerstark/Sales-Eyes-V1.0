# Sales Stalker Day 2 - Quick Start Guide

## What Was Built
A complete AI-powered research pipeline that converts freeform prospect input into structured research plans, collects findings, and generates customized sales scripts using DeepSeek AI.

## Starting the App

### Prerequisites
- Docker & Docker Compose installed
- DeepSeek API key (from https://api.deepseek.com)
- Or use without DeepSeek for testing (will see errors on plan generation)

### Run
```bash
# From project root
docker-compose up

# In about 30-60 seconds:
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000/api/health
```

### Database
- Postgres automatically initializes from `database/init.sql`
- New tables: `research_sessions`, `plan_steps`, `findings`
- Connection string in `docker-compose.yml` (no changes needed)

## User Journey

### 1. Create Account
- Go to http://localhost:3000/register
- Enter email + password (min 8 chars)
- Login

### 2. Enter Prospect Info (New!)
- Homepage now has single large textarea
- Type anything you know: company name, prospect role, background, interests
- Click "Start research"

### 3. View Plan & Findings (New!)
- Redirects to `/research/[sessionId]`
- Shows research plan (e.g., "Company Intelligence", "Pain Point Detection")
- Empty findings area (will populate when agents run)
- **Note**: To populate findings, you need a valid DeepSeek API key

### 4. Select Findings (New!)
- Click checkboxes on finding cards to select them
- Each finding shows confidence/relevancy scores
- Continue button enabled after selection

### 5. Choose Methodology (New!)
- SPIN, Challenger, or Sandler framework
- Or enter custom approach
- "Generate Script" button

### 6. View & Export Result (New!)
- Generated sales script displayed
- Copy to clipboard
- Download as .txt file
- Start new research or go to dashboard

## Configuration

### Set DeepSeek API Key
**Option 1: Environment Variable (Development)**
```bash
# Edit .env file
DEEPSEEK_API_KEY=sk-your-key-here
docker-compose up --build
```

**Option 2: Settings Modal (Runtime)**
- Click gear icon (top-right, requires auth)
- Enter DeepSeek API key in modal
- Saves to browser localStorage
- **Note**: Settings are client-side only; will be user-specific in future

### Endpoints Configured
```
DeepSeek:  https://api.deepseek.com/v1/chat/completions (default, editable)
NewsAPI:   https://newsapi.org/v2 (future, optional)
```

## File Structure Summary

**Frontend** (Next.js, TypeScript, Tailwind)
- `app/page.tsx` - Freeform input form
- `app/research/[sessionId]/page.tsx` - Plan + findings view
- `app/research/[sessionId]/style/page.tsx` - Methodology picker
- `app/research/[sessionId]/results/page.tsx` - Final script
- `components/SettingsModal.tsx` - API key settings
- `app/globals.css` - Maroon + black theme
- `tailwind.config.ts` - Color palette

**Backend** (FastAPI, SQLAlchemy, Async)
- `routes/research.py` - 6 new endpoints
- `services/deepseek_service.py` - AI integration
- `services/research_service.py` - Business logic
- `models/research.py` - SQLAlchemy ORM

**Database** (PostgreSQL)
- `research_sessions` - Main container
- `plan_steps` - Individual research tasks
- `findings` - Research results with scores
- `user_settings` - API keys (extended)

## Troubleshooting

### "Session not found" Error
- Verify JWT token in localStorage
- Check session ID is correct UUID
- Session might have expired

### "Failed to generate plan"
- Check DEEPSEEK_API_KEY is set in .env
- Verify key is valid and has credits
- Check network connectivity to api.deepseek.com

### Findings Not Appearing
- Currently, DeepSeek returns mock findings in the plan
- Actual findings table integration happens Day 3+
- To test: check plan steps load correctly

### Settings Modal Not Opening
- Must be authenticated (logged in)
- Must be on an authenticated page (not /, /login, /register)
- Gear icon appears in header

### Styling Issues (Maroon not Showing)
- Clear browser cache: Ctrl+Shift+Del
- Tailwind needs rebuild: docker-compose up --build
- Check globals.css loaded (inspect → Styles tab)

## API Endpoints Reference

### Research Sessions
```
POST   /api/research/sessions                      Create session
GET    /api/research/sessions/{id}                 Get session with plan
POST   /api/research/sessions/{id}/plan            Generate plan
GET    /api/research/sessions/{id}/findings        List findings
POST   /api/research/sessions/{id}/findings/select Mark findings selected
POST   /api/research/sessions/{id}/generate-script Create script
```

### Example Flow
```bash
# 1. Create session
curl -X POST http://localhost:8000/api/research/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prospect_input":"VP Sales at TechCorp, AI interested"}'

# Returns: {"id": "uuid", "status": "planning", ...}

# 2. Generate plan
curl -X POST http://localhost:8000/api/research/sessions/{id}/plan \
  -H "Authorization: Bearer $TOKEN"

# 3. Poll for findings
curl http://localhost:8000/api/research/sessions/{id} \
  -H "Authorization: Bearer $TOKEN"

# 4. Select findings & generate
curl -X POST http://localhost:8000/api/research/sessions/{id}/generate-script \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"methodology":"SPIN","finding_ids":["uuid1","uuid2"]}'
```

## Design System

**Colors** (Maroon + Black)
- Background: `#0a0a0a` (black)
- Primary: `#3d1730` to `#2a0f21` (deep maroon)
- Accent: `#8d3b6f` (mid maroon)
- Text: white / white-70 (reduced opacity for hierarchy)

**Typography**
- Headings: Bold, `text-maroon-500`
- Body: Regular, white
- Accents: Smaller, `text-maroon-400`

**Motion**
- Fade-in on page load
- Spinner during async operations
- Pulse on in-progress steps
- Smooth transitions on all interactions

## Next Steps

### Short Term (Day 3)
1. Implement actual agent execution (Company Intelligence, Pain Point Detection, etc.)
2. Store findings in DB instead of mocking from DeepSeek
3. Real-time findings streaming as agents run

### Medium Term (Day 4-5)
1. Session history / dashboard view
2. Findings validation & editing UI
3. WebSocket for live progress updates

### Long Term (Day 6+)
1. User-specific API key management (per-user settings table)
2. Document upload for voice/style matching
3. A/B testing different methodologies
4. CRM integration

## Testing Checklist

- [ ] Register & login
- [ ] Submit freeform prospect input
- [ ] Verify research page loads
- [ ] Check plan steps display
- [ ] Open settings modal with gear icon
- [ ] Enter dummy DeepSeek key in settings
- [ ] Verify it persists (reload page)
- [ ] Select findings & advance
- [ ] Choose SPIN methodology
- [ ] Verify script generates
- [ ] Copy to clipboard works
- [ ] Download creates .txt file
- [ ] Mobile layout responsive
- [ ] Maroon colors display correctly
- [ ] Animations play smoothly

## Support

If you hit issues:
1. Check `.env` file for required keys
2. Review docker logs: `docker-compose logs backend` / `docker-compose logs frontend`
3. Browser dev tools (F12) for frontend errors
4. Verify database health: `docker exec sales_stalker_db psql -U salesstalker -d sales_stalker -c "\dt"`

---

**Status**: All core features implemented. Ready for agent integration and findings population.
