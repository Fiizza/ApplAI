# APPLAI: AI Career Copilot

APPLAI is an AI-powered career assistant that simplifies the job application process by helping users manage applications, tailor resumes for Applicant Tracking Systems (ATS), generate personalized cover letters, prepare for interviews, analyze skill gaps, and track recruiter communications.



## Overview

APPLAI combines modern web technologies with Large Language Models (LLMs) to provide an intelligent job search experience. The platform automates repetitive tasks and offers AI-driven insights to help users stay organized and improve their chances of landing interviews.



## Key Features

- User authentication with JWT
- Job application tracking dashboard
- AI-powered job description parsing
- ATS resume tailoring
- Resume upload (PDF)
- AI-generated cover letters
- Interview preparation assistance
- Skill gap analysis
- Personalized learning recommendations
- Gmail recruiter email integration
- Daily reminder digests
- Application status tracking


## Technology Stack

| Category | Technologies |
|----------|--------------|
| Frontend | React (Vite), JavaScript, CSS |
| Backend | FastAPI, SQLAlchemy, SQLite, APScheduler |
| AI | Google Gemini API |
| Authentication | JWT, Google OAuth |
| Deployment | Docker, Vercel |



## Project Structure

```text
.
├── app/                  # FastAPI backend
├── frontend/             # React frontend
├── requirements.txt
├── Dockerfile
├── README.md
└── .gitignore
```



## Configuration

### Backend Environment Variables

Create a `.env` file and configure the following variables:

```env
GEMINI_API_KEY=

GOOGLE_CLIENT_ID=

GOOGLE_CLIENT_SECRET=

GOOGLE_REDIRECT_URI=

FRONTEND_URL=
```

### Frontend Environment Variables

```env
VITE_API_URL=
```



## Running the Application

1. Install the backend dependencies from `requirements.txt`.
2. Install the frontend dependencies using `npm install`.
3. Configure the required environment variables.
4. Start the FastAPI backend.
5. Start the React development server.

The backend exposes interactive API documentation through Swagger UI.


## Deployment

### Frontend

Deploy the React application to **Vercel** and configure the backend API URL through the `VITE_API_URL` environment variable.

### Backend

The backend is Dockerized and can be deployed to any platform that supports Docker containers. Configure the required environment variables before deployment.



## Future Improvements

- Multiple resume management
- AI mock interviews
- Job recommendation engine
- Calendar integration
- Application analytics
- Notification center



## License

This project is intended for educational and portfolio purposes.



## Author

**Fizza Akram**


**Interests**

- Generative AI
- Large Language Models (LLMs)
- Retrieval-Augmented Generation (RAG)
- Agentic AI Workflows
- FastAPI
- React