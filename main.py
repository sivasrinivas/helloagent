import json
import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from urllib import request
from urllib.error import URLError

app = FastAPI()
conversation_index: dict[str, dict[str, Any]] = {}


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

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:latest").strip()

llm = ChatOllama(
    base_url=OLLAMA_HOST,
    model=OLLAMA_MODEL,
    temperature=0,
)

memory = InMemorySaver()


def call_model(state: MessagesState) -> MessagesState:
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

graph_builder = StateGraph(MessagesState)
graph_builder.add_node("call_model", call_model)
graph_builder.add_edge(START, "call_model")
graph_builder.add_edge("call_model", END)
chat_graph = graph_builder.compile(checkpointer=memory)


def _extract_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return str(content)


def _serialize_messages(messages: list[BaseMessage]) -> list[dict[str, str]]:
    serialized: list[dict[str, str]] = []
    for msg in messages:
        role = "assistant"
        if isinstance(msg, HumanMessage):
            role = "user"
        elif isinstance(msg, AIMessage):
            role = "assistant"
        serialized.append({"role": role, "content": _extract_text(msg.content)})
    return serialized


def _get_thread_messages(session_id: str) -> list[BaseMessage]:
    config = {"configurable": {"thread_id": session_id}}
    state = chat_graph.get_state(config=config)
    values = getattr(state, "values", None) or {}
    messages = values.get("messages", [])
    return messages if isinstance(messages, list) else []


def _touch_conversation(session_id: str, first_message: str) -> None:
    entry = conversation_index.setdefault(
        session_id,
        {
            "session_id": session_id,
            "title": first_message[:60] or f"Conversation {session_id[:8]}",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    entry["updated_at"] = datetime.now(timezone.utc).isoformat()


@app.post("/chats")
async def chat(session_id: str, message: str):
    config = {"configurable": {"thread_id": session_id}}
    graph_input = {"messages": [HumanMessage(content=message)]}

    try:
        _touch_conversation(session_id, message)
        result = chat_graph.invoke(graph_input, config=config)
        final_message = result["messages"][-1]
        if isinstance(final_message, AIMessage):
            answer = _extract_text(final_message.content)
        else:
            answer = str(final_message)
        return {"status": "ok", "session_id": session_id, "answer": answer}
    except Exception as err:
        return {"status": "error", "reason": str(err)}


@app.post("/conversations")
async def create_conversation() -> dict[str, str]:
    session_id = uuid4().hex
    _touch_conversation(session_id, "")
    return {"status": "ok", "session_id": session_id}


@app.get("/conversations")
async def list_conversations() -> dict[str, list[dict[str, Any]]]:
    conversations = sorted(
        conversation_index.values(),
        key=lambda item: item.get("updated_at", ""),
        reverse=True,
    )
    return {"conversations": conversations}


@app.get("/conversations/{session_id}")
async def get_conversation(session_id: str) -> dict[str, Any]:
    messages = _get_thread_messages(session_id)
    return {
        "session_id": session_id,
        "messages": _serialize_messages(messages),
        "exists": session_id in conversation_index or bool(messages),
    }


@app.get("/health")
async def health():
    # call Ollama tags endpoint and verify configured model exists
    url = f"{OLLAMA_HOST}/api/tags"

    try:
        with request.urlopen(url, timeout=3) as response:
            if response.status == 200:
                payload = json.loads(response.read().decode("utf-8"))
                available_models = {item.get("name", "") for item in payload.get("models", [])}

                if OLLAMA_MODEL and OLLAMA_MODEL not in available_models:
                    requested_base = OLLAMA_MODEL.split(":", 1)[0]
                    available_bases = {name.split(":", 1)[0] for name in available_models if name}
                    if requested_base not in available_bases:
                        return {"status": "error", "reason": f"model_not_found: {OLLAMA_MODEL}"}
                return {"status": "ok"}
        return {"status": "error", "reason": "ollama_unreachable"}
    except (URLError, TimeoutError) as err:
        return {"status": "error", "reason": str(err)}


@app.get("/")
async def root():
    return {"message": "Hello World"}
