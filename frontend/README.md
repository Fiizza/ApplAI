# Career Copilot — frontend

```
npm install
npm run dev
```

Runs at http://localhost:5173, talks to your FastAPI backend at http://localhost:8000
(already whitelisted in main.py's CORS config). Start the backend first:

```
uvicorn app.main:app --reload
```

Change `BASE` in `src/api.js` if your backend runs elsewhere.

## What's wired up
- Register / login (JWT stored in localStorage)
- Kanban board (Applied / Interview / Offer / Rejected) with status dropdown + delete
- Add application: paste a job URL or description → parse → review → save
- Per-application actions: skill match, cover letter opener, interview prep,
  follow-up email, tailored resume, learning recommendations
- Skills page (add/remove your reference skill set)
- Resume page (paste text or upload a PDF)

## Not included yet
- Job search/discovery (finding postings, not just parsing pasted ones)
- Drag-and-drop between kanban columns (status changes via dropdown for now)
