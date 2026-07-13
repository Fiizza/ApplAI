# APPLAI: AI Career Copilot

AI Career Copilot is an AI-powered job application assistant that helps users manage job applications, tailor resumes, generate cover letters, prepare for interviews, track recruiter emails, and receive intelligent reminders.

## Features

- User Authentication (JWT)
- Job Application Tracking
- AI Job Description Parsing
- Resume Upload (PDF)
- Resume Tailoring for ATS
- AI Cover Letter Generation
- Interview Preparation
- Skill Gap Analysis
- Learning Recommendations
- Gmail Recruiter Email Integration
- Daily Reminder Digests
- Application Status Tracking

---

## Tech Stack

### Frontend
- React (Vite)
- JavaScript
- CSS

### Backend
- FastAPI
- SQLAlchemy
- SQLite
- APScheduler

### AI
- Google Gemini API

### Authentication
- JWT
- Google OAuth (Gmail)

---

## Project Structure

```
.
├── app/                  # FastAPI Backend
├── frontend/             # React Frontend
├── requirements.txt
├── Dockerfile
├── README.md
└── .gitignore
```

---

## Installation

### Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
cd YOUR_REPOSITORY
```

---

## Backend Setup

Create a virtual environment.

```bash
python -m venv venv
```

Activate it.

Windows

```bash
venv\Scripts\activate
```

Linux/macOS

```bash
source venv/bin/activate
```

Install dependencies.

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root.

Example:

```env
GEMINI_API_KEY=YOUR_API_KEY

GOOGLE_CLIENT_ID=YOUR_CLIENT_ID

GOOGLE_CLIENT_SECRET=YOUR_CLIENT_SECRET

GOOGLE_REDIRECT_URI=http://localhost:8000/auth/gmail/callback

FRONTEND_URL=http://localhost:5173
```

Run the backend.

```bash
uvicorn app.main:app --reload
```

Backend:

```
http://localhost:8000
```

Swagger Documentation:

```
http://localhost:8000/docs
```

---

## Frontend Setup

Navigate to the frontend folder.

```bash
cd frontend
```

Install packages.

```bash
npm install
```

Create a `.env` file.

```env
VITE_API_URL=http://localhost:8000
```

Run the frontend.

```bash
npm run dev
```

Frontend:

```
http://localhost:5173
```

---

## Deployment

### Frontend

Deploy on **Vercel**.

Environment Variable:

```
VITE_API_URL=https://YOUR_BACKEND_URL
```

---

### Backend

Deploy on **Hugging Face Spaces (Docker SDK)**.

Required Environment Variables:

```
GEMINI_API_KEY

GOOGLE_CLIENT_ID

GOOGLE_CLIENT_SECRET

GOOGLE_REDIRECT_URI

FRONTEND_URL
```

The backend runs using:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 7860
```

---

## API Documentation

After deployment:

```
https://YOUR_SPACE_NAME.hf.space/docs
```

---

## License

This project is intended for educational and portfolio purposes.