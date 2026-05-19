# Resume Analyzer

Full-stack resume analyzer with a React frontend, FastAPI backend, PostgreSQL database, and Microsoft Graph mailbox intake.

## Run

From the project root:

```bash
docker compose up --build
```

Open:

```text
http://localhost:3000
```

When running the frontend locally with `npm run dev`, Vite opens the sign-in page in your browser automatically.

Default sign-in:

```text
Username: TEK-1
Email: rochisna.g@tektalis.com
Password: Tek@12345
```

## Environment

`backend/.env` is local only and is ignored by Git. Create it from the example when setting up a new machine:

```bash
copy backend\.env.example backend\.env
```

Then fill in local API keys and Microsoft Graph settings.

## Stop

```bash
docker compose down
```

Use this only when you want to delete the local PostgreSQL data too:

```bash
docker compose down -v
```
