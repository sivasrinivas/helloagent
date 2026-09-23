# helloagent

A simple conversational and RAG agent using FastAPI, LangGraph, Redis, Qdrant, and a local Ollama model.

## Local Setup

1. Create and activate a virtual environment.
2. Install dependencies (for example: `fastapi`, `uvicorn`, `streamlit`).
3. Copy environment template:
   - `cp .env.example .env`
4. Start Ollama and ensure your model is available:
   - `ollama pull llama3.1:latest`
5. Run the API:
   - `./run.sh`
   - or `uv run uvicorn main:app --reload`
6. Run Streamlit UI (in a separate terminal):
   - `uv run streamlit run streamlit_app.py`

## Chat UI Features

- ChatGPT-like chat interface using Streamlit chat components.
- Sidebar conversation list to resume previous sessions.
- "New chat" action to create and switch to a fresh conversation.

## Environment Variables

Define local values in `.env`:

- `OLLAMA_HOST` (example: `http://localhost:11434`)
- `OLLAMA_MODEL` (example: `llama3.1:latest`)
- `API_BASE_URL` for Streamlit (optional; defaults to `http://127.0.0.1:8000`)

Keep `.env.example` committed with safe placeholder/default values only.

## Security Notes (Public Repository)

- Never commit secrets, tokens, keys, passwords, cookies, or private certificates.
- Never commit internal/company-specific URLs, IDs, runbooks, or incident details.
- `.env` is ignored by git; use `.env.example` for shared configuration shape.
- Before pushing, run `git status` and verify no sensitive files are staged.
