# AI FinOps Proxy - EigenMinds

AI FinOps Proxy is an OpenAI-compatible gateway that intercepts AI requests,
tracks token usage and cost, enforces per-consumer budgets, and routes requests
to the most appropriate local model.

## Architecture

- **Core proxy:** FastAPI endpoint in `app/main.py` and `app/api/routes.py`.
- **Cost tracking:** SQLite storage in `app/db/database.py`.
- **AI routing:** Complexity- and budget-aware routing in `app/core/router.py`.
- **Dashboard:** Streamlit reporting application in `dashboard/app.py`.

The default setup uses two Ollama providers:

| Provider | Model | Base URL | Input / output cost per 1M tokens |
| --- | --- | --- | --- |
| A (fast / low cost) | `llama3.2:3b` | `http://localhost:11434/v1` | $0.06 / $0.06 |
| B (slower / higher quality) | `mistral:7b` | `http://localhost:11435/v1` | $0.24 / $0.24 |

## Getting started

1. Create a virtual environment:
   `python -m venv venv`
2. Activate it (`venv\Scripts\activate` on Windows).
3. Install dependencies:
   `pip install -r requirements.txt`
4. Start the services:
   `docker compose up --build`

The proxy listens on port `8000`; the dashboard listens on port `8501`.

Every request must include an `X-Consumer-ID` header. Example:

```bash
curl http://localhost:8000/v1/chat/completions ^
  -H "Content-Type: application/json" ^
  -H "X-Consumer-ID: equipo_desarrollo" ^
  -d "{\"model\":\"auto\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello\"}]}"
```

## Development

Run the tests with:

```bash
pytest
```

Local secrets belong in `.env`, which is ignored by Git. Use `.env.example` as
the safe template. Do not commit API keys, database files, virtual
environments, IDE settings, logs, or cache directories.

See [`INSTRUCCIONES.md`](INSTRUCCIONES.md) and [`CHALLENGE.md`](CHALLENGE.md)
for the starter-kit documentation and the complete challenge specification.
