from pickle import HIGHEST_PROTOCOL
from fastapi import FastAPI
import json
import os
from urllib import request
from urllib.error import URLError

app = FastAPI()

conversation_store: dict[str, list[dict[str, str]]] = {}
MAX_TURNS = 8

ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
ollama_model = os.getenv("OLLAMA_MODEL", "").strip()

# load environment variables
def load_dotenv(path: str = ".env") -> None:
    """Minimal .env loader for local development."""
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


load_dotenv()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/chats")
async def chat(session_id: str, message: str):
    # get/create session history
    history = conversation_store.setdefault(session_id, [])
    history.append({"role": "user", "content": message})

    # keep context bounded
    context_messages = history[-(MAX_TURNS * 2)]

    pass


@app.get("/health")
async def health():
    # call Ollama tags endpoint and verify configured model exists
    url = f"{ollama_host}/api/tags"

    # debug
    print(url)

    try:
        with request.urlopen(url, timeout=3) as response:
            if response.status == 200:
                payload = json.loads(response.read().decode("utf-8"))
                available_models = {item.get("name", "") for item in payload.get("models", [])}

                if ollama_model and ollama_model not in available_models:
                    requested_base = ollama_model.split(":", 1)[0]
                    available_bases = {name.split(":", 1)[0] for name in available_models if name}
                    if requested_base not in available_bases:
                        return {"status": "error", "reason": f"model_not_found: {ollama_model}"}
                return {"status": "ok"}
        return {"status": "error", "reason": "ollama_unreachable"}
    except (URLError, TimeoutError) as err:
        return {"status": "error", "reason": str(err)}
