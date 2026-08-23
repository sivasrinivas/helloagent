# helloagent

A simple conversational and RAG agent using FastAPI, LangGraph, Redis, Qdrant, and a local Ollama model.

## Local Setup

1. Create and activate a virtual environment.
2. Install dependencies (for example: `fastapi`, `uvicorn`).
3. Copy environment template:
   - `cp .env.example .env`
4. Start Ollama and ensure your model is available:
   - `ollama pull llama3.1:latest`
5. Run the API (for example with uvicorn):
   - `uvicorn main:app --reload`

## Environment Variables

Define local values in `.env`:

- `OLLAMA_HOST` (example: `http://localhost:11434`)
- `OLLAMA_MODEL` (example: `llama3.1:latest`)

Keep `.env.example` committed with safe placeholder/default values only.

## Security Notes (Public Repository)

- Never commit secrets, tokens, keys, passwords, cookies, or private certificates.
- Never commit internal/company-specific URLs, IDs, runbooks, or incident details.
- `.env` is ignored by git; use `.env.example` for shared configuration shape.
- Before pushing, run `git status` and verify no sensitive files are staged.
