import json
import os
from fastapi import FastAPI
from langchain_core.messages import AIMessage, HumanMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from urllib import request
from urllib.error import URLError

app = FastAPI()


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
    print("messages before calling model: ", state["messages"])
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

graph_builder = StateGraph(MessagesState)
graph_builder.add_node("call_model", call_model)
graph_builder.add_edge(START, "call_model")
graph_builder.add_edge("call_model", END)
chat_graph = graph_builder.compile(checkpointer=memory)


@app.post("/chats")
async def chat(session_id: str, message: str):
    config = {"configurable": {"thread_id": session_id}}
    graph_input = {"messages": [HumanMessage(content=message)]}

    try:
        result = chat_graph.invoke(graph_input, config=config)
        final_message = result["messages"][-1]
        if isinstance(final_message, AIMessage):
            answer = final_message.content
        else:
            answer = str(final_message)
        return {"status": "ok", "session_id": session_id, "answer": answer}
    except Exception as err:
        return {"status": "error", "reason": str(err)}


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
