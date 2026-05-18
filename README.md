# Resume Analyzer

Full-stack resume analyzer with:

- React frontend
- FastAPI backend
- PostgreSQL database
- Microsoft Graph mailbox intake every 2 minutes

The easiest way to run this project on another system is with Docker.

## What Docker Does Here

Docker runs the project in 3 containers:

- `db`: PostgreSQL database
- `backend`: FastAPI API on port `8000`
- `frontend`: React app on port `3000`

You do not need to manually install PostgreSQL or Python packages when using Docker.

The Docker backend uses `backend/requirements-docker.txt`, which skips the optional `sentence-transformers` package so setup stays much faster. The app still runs using TF-IDF, skill matching, and Groq analysis. Native local setup can use the full `backend/requirements.txt`.

## Prerequisites

Install these first:

- Git: https://git-scm.com/downloads
- Docker Desktop: https://www.docker.com/products/docker-desktop/

After installing Docker Desktop, open it once and keep it running.

## Run Locally With Docker

### 1. Clone The Project

```bash
git clone <your-github-repo-url>
cd resume-analyzer
```

### 2. Backend Environment File

`backend/.env` is local only and should not be pushed to GitHub because it can contain API keys and Microsoft credentials.

Create it from the template:


```bash
cp backend/.env.example backend/.env
```

On Windows PowerShell, use:

```powershell
Copy-Item backend/.env.example backend/.env
```

Open `backend/.env` and fill in your local values.

Minimum required values:

```env
GROQ_API_KEY=your_groq_api_key_here

MAIL_AUTH_METHOD=graph
MAIL_USERNAME=careers@example.com
MAIL_FROM=careers@example.com
MS_TENANT_ID=your_microsoft_tenant_id_or_common
MS_CLIENT_ID=your_microsoft_app_client_id
MS_CLIENT_SECRET=your_microsoft_app_client_secret_if_using_background_graph_access

MAIL_AUTO_POLL_ENABLED=true
MAIL_POLL_INTERVAL_SECONDS=120
```

Do not change `DATABASE_URL` for Docker. `docker-compose.yml` sets the correct database URL automatically inside the backend container.

### 3. Start The App

From the project root, one command starts PostgreSQL, the FastAPI backend, and the React frontend:

```bash
docker compose up --build
```

The first run can take several minutes because Docker downloads images and installs dependencies.

When it is ready, open:

- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs

### 4. Use The App

1. Open http://localhost:3000
2. Configure your job roles.
3. Upload resumes manually, or open `Upload > Graph intake`.
4. The app checks the Microsoft Graph mailbox every 2 minutes.
5. Resume results appear in the leaderboard.

## Stop The App

Press `Ctrl + C` in the terminal running Docker.

Then run:

```bash
docker compose down
```

This stops the containers but keeps the PostgreSQL data.

To remove the database data also:

```bash
docker compose down -v
```

Use `-v` only when you want a fresh database.

## Useful Docker Commands

Start again:

```bash
docker compose up
```

Rebuild after code changes:

```bash
docker compose up --build
```

See running containers:

```bash
docker compose ps
```

View backend logs:

```bash
docker compose logs -f backend
```

View frontend logs:

```bash
docker compose logs -f frontend
```

View database logs:

```bash
docker compose logs -f db
```

## GitHub Push Notes

Do not push generated files.

This project includes `.gitignore` for:

- Python virtual environments
- `backend-java/` legacy Java backend files
- `node_modules`
- build output
- logs
- uploaded resumes
- Microsoft token cache

Before pushing, check:

```bash
git status
```

You should push these important setup files:

- `README.md`
- `docker-compose.yml`
- `backend/Dockerfile`
- `backend/requirements-docker.txt`
- `frontend/Dockerfile`
- `backend/.env.example`
- `.gitignore`

You should not push:

- `backend/.env`
- `backend-java/`
- `backend/uploads/`
- `frontend/node_modules/`
- `backend/venv/`
- `*.log`

## Run Without Docker

Use this only if you want to run everything manually.

### Backend

```bash
cd backend
python -m venv venv
```

Windows:

```powershell
venv\Scripts\activate
```

macOS/Linux:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create and edit env:

```bash
cp .env.example .env
```

Run backend:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

If PowerShell blocks `npm`, use:

```powershell
npm.cmd run dev
```

Frontend runs at:

```text
http://localhost:3000
```

## Project Structure

```text
resume-analyzer/
├── backend/
│   ├── main.py
│   ├── analyzer.py
│   ├── database.py
│   ├── models.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
├── docker-compose.yml
├── .gitignore
└── README.md
```

## Troubleshooting

### Docker Desktop is not running

Start Docker Desktop first, then run:

```bash
docker compose up --build
```

### Port already in use

If port `3000`, `8000`, or `5432` is already used, stop the other app or change the port mapping in `docker-compose.yml`.

Example:

```yaml
ports:
  - "3001:3000"
```

### Backend cannot connect to database

Rebuild and restart:

```bash
docker compose down
docker compose up --build
```

### Need a fresh database

```bash
docker compose down -v
docker compose up --build
```

### Frontend opens but API calls fail

Make sure the backend is running:

```bash
docker compose ps
```

Backend should be available at:

```text
http://localhost:8000/docs
```
