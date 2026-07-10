# Frontend — Deep Research Agent

React + TypeScript + Vite. Renders the agent's live trace (SSE) and the final cited report.

## Setup

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (proxies API to :8000)
```

Run the backend (`uv run uvicorn app.main:app --reload`) alongside it.

## Scripts

- `npm run dev` — dev server with API proxy
- `npm run build` — type-check + production build
- `npm run typecheck` — strict TypeScript check only
