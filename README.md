# IELTS Practice Platform

An IELTS practice and grading website with AI-powered writing feedback. Minimal design, full-stack (React + FastAPI + PostgreSQL), deployable to Render.

## Quick Start (Local)

### 1. Prerequisites
- Python 3.11+ with venv
- Node.js 18+
- PostgreSQL running locally (or use Render DB for testing)

### 2. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy and edit .env
cp .env.example .env
# → Fill in DATABASE_URL, JWT_SECRET (any random string), POE_API_KEY

# Run migrations
alembic upgrade head

# Start backend
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd frontend
cp .env.example .env
# → VITE_API_BASE_URL defaults to http://localhost:8000

npm install
npm run dev
```

Open http://localhost:5173

### 4. Create Admin User

```bash
cd backend
source venv/bin/activate
python ../scripts/create_admin.py --email admin@example.com --password yourpassword
```

## Manual Steps (YOU MUST DO THESE)

### 🔑 Poe API Key
1. Get your API key from [Poe](https://poe.com/api)
2. Set `POE_API_KEY` in `backend/.env`
3. **Verify the model name**: The default is `gpt-5.4-nano`. Check Poe's documentation for the exact model name — if it doesn't match, you'll get "model not found" errors. Change `POE_MODEL` in `.env` or Render dashboard if needed.
4. If the small model's grading quality isn't good enough, switch `POE_MODEL` to a stronger model (e.g., `gpt-4o`, `claude-sonnet-4-5`).

### 📝 Convert Your Existing Content
1. The conversion script is at `scripts/convert.py`
2. **You must edit the `parse_markdown()` function** to match your actual `.md` file format
3. Search for `TODO:` in that file — it marks exactly what you need to change
4. The placeholder parser assumes: question lines, choice lines A/B/C/D, answers marked `Answer: B`
5. Run it: `python scripts/convert.py path/to/your/file.md`

### 📚 Add Real Content
1. Place your IELTS questions under `content/` following the structure:
   - `content/reading/<passage-id>/meta.json` (+ optional PDF)
   - `content/listening/<section-id>/meta.json` (+ MP3 audio)
   - `content/writing/<task-id>/meta.json`
2. See the placeholder samples in `content/` for the exact JSON format
3. For listening tests, add `.mp3` files alongside the `meta.json`

### ☁️ Deploy to Render
1. Push this repo to GitHub
2. In `render.yaml`, replace `YOUR_USERNAME` with your GitHub username
3. Go to [dashboard.render.com](https://dashboard.render.com) → Blueprint → connect your repo
4. After deployment, manually set `POE_API_KEY` in the backend service's environment variables
5. Frontend will be at `https://ielts-frontend.onrender.com`

## Content Format

### Reading / Listening (`meta.json`)
```json
{
  "id": "reading-passage-01",
  "type": "reading",
  "title": "The History of Tea",
  "pdf": "passage.pdf",
  "audio": null,
  "questions": [
    {
      "id": "q1",
      "number": 1,
      "prompt": "What was the main reason...?",
      "choices": ["A. Option one", "B. Option two", "C. Option three", "D. Option four"],
      "answer": "B"
    }
  ]
}
```

### Writing (`meta.json`)
```json
{
  "id": "writing-task2-01",
  "type": "writing",
  "task": "task1",
  "title": "Line Graph - Energy Consumption",
  "prompt": "The graph below shows... Summarise the information...",
  "word_minimum": 150
}
```

## Project Structure

```
ielts-practice/
├── backend/            # FastAPI (Python)
│   ├── app/
│   │   ├── main.py           # App entry point
│   │   ├── config.py         # Env var settings
│   │   ├── database.py       # SQLAlchemy engine
│   │   ├── models.py         # ORM models
│   │   ├── schemas.py        # Pydantic schemas
│   │   ├── auth.py           # JWT + password hashing
│   │   ├── routers/          # API route handlers
│   │   └── services/         # Business logic (loader, grader)
│   └── alembic/              # Database migrations
├── frontend/           # React + Vite + Tailwind
│   └── src/
│       ├── context/          # AuthContext
│       ├── components/       # Shared components
│       └── pages/            # Route pages
├── content/            # IELTS question bank (git-tracked)
├── scripts/            # Utility scripts
└── render.yaml         # Render Blueprint deploy config
```

## API Overview

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /api/auth/register | No | Create account |
| POST | /api/auth/login | No | Get JWT token |
| GET | /api/auth/me | Yes | Current user info |
| GET | /api/questions?type=reading | No | List questions by type |
| GET | /api/questions/{id} | No | Get question (answers stripped) |
| POST | /api/grade/objective | Yes | Submit reading/listening answers |
| POST | /api/grade/writing | Yes | Submit essay for AI grading |
| GET | /api/attempts | Yes | User's attempt history |
| GET | /api/admin/users | Admin | All users |
| GET | /api/admin/attempts | Admin | All attempts |

## Tech Stack

- **Frontend**: React 18, Vite, React Router 6, Tailwind CSS 3, Recharts, Lucide React
- **Backend**: FastAPI, SQLAlchemy 2.x, Alembic, python-jose (JWT), passlib (bcrypt)
- **Database**: PostgreSQL
- **AI Grading**: Poe API (OpenAI-compatible endpoint)
- **Deploy**: Render (Blueprint)
