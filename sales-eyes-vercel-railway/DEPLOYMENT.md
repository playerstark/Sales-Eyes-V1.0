# Sales-Eyes Deployment Package

Recommended deployment:
- Vercel: set Root Directory to `frontend`
- Railway: set Root Directory to `backend`
- Railway: add a PostgreSQL service
- Configure environment variables from `.env.example`
- FastAPI should listen on `0.0.0.0` and Railway's `$PORT`

This package is intended to be extracted into the GitHub repository so
`frontend/`, `backend/`, and `database/` are visible at repository root.
