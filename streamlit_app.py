import json
import os
from urllib import parse, request
from urllib.error import URLError

import streamlit as st


def load_dotenv(path: str = ".env") -> None:
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
DEFAULT_API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def api_get(path: str, api_base_url: str) -> dict:
    url = f"{api_base_url}{path}"
    req = request.Request(url=url, method="GET")
    with request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_post(path: str, api_base_url: str) -> dict:
    url = f"{api_base_url}{path}"
    req = request.Request(url=url, method="POST")
    with request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def create_conversation(api_base_url: str) -> str:
    data = api_post("/conversations", api_base_url)
    return str(data["session_id"])


def load_conversations(api_base_url: str) -> list[dict]:
    data = api_get("/conversations", api_base_url)
    return data.get("conversations", [])


def load_messages(session_id: str, api_base_url: str) -> list[dict]:
    data = api_get(f"/conversations/{session_id}", api_base_url)
    return data.get("messages", [])


def send_message(session_id: str, message: str, api_base_url: str) -> dict:
    query = parse.urlencode({"session_id": session_id, "message": message})
    return api_post(f"/chats?{query}", api_base_url)


def check_api_health(api_base_url: str) -> tuple[bool, str]:
    try:
        response = api_get("/health", api_base_url)
        if response.get("status") == "ok":
            return True, "Connected"
        return False, f"API reachable but unhealthy: {response}"
    except (URLError, TimeoutError) as err:
        return False, str(err)


def app() -> None:
    st.set_page_config(page_title="HelloAgent Chat", page_icon="🤖", layout="wide")
    st.title("HelloAgent")
    st.caption("LangGraph + Ollama")

    if "selected_session_id" not in st.session_state:
        st.session_state.selected_session_id = ""

    if "last_error" not in st.session_state:
        st.session_state.last_error = ""

    if "api_base_url" not in st.session_state:
        st.session_state.api_base_url = DEFAULT_API_BASE_URL

    with st.sidebar:
        st.header("Conversations")
        st.session_state.api_base_url = st.text_input(
            "FastAPI base URL",
            value=st.session_state.api_base_url,
            help="Where Streamlit should call your FastAPI backend.",
        ).rstrip("/")

        is_healthy, health_message = check_api_health(st.session_state.api_base_url)
        if is_healthy:
            st.success("API connected")
        else:
            st.error(f"API unavailable: {health_message}")
            st.caption("Start backend: `uv run uvicorn main:app --reload`")
            st.stop()

        if st.button("New chat", use_container_width=True):
            try:
                st.session_state.selected_session_id = create_conversation(st.session_state.api_base_url)
                st.session_state.last_error = ""
                st.rerun()
            except Exception as err:
                st.session_state.last_error = str(err)

        try:
            conversations = load_conversations(st.session_state.api_base_url)
        except (URLError, TimeoutError) as err:
            st.error(f"Cannot load conversations: {err}")
            conversations = []

        if conversations:
            options = [item["session_id"] for item in conversations]
            labels = {
                item["session_id"]: f"{item.get('title', 'Conversation')} ({item['session_id'][:8]})"
                for item in conversations
            }

            if st.session_state.selected_session_id not in options:
                st.session_state.selected_session_id = options[0]

            selected = st.radio(
                "Pick a conversation",
                options=options,
                format_func=lambda session_id: labels.get(session_id, session_id),
                index=options.index(st.session_state.selected_session_id),
            )
            st.session_state.selected_session_id = selected
        else:
            st.info("No conversations yet. Start one.")

    if st.session_state.last_error:
        st.error(st.session_state.last_error)

    session_id = st.session_state.selected_session_id
    if not session_id:
        st.stop()

    st.caption(f"Session: `{session_id}`")

    try:
        messages = load_messages(session_id, st.session_state.api_base_url)
    except (URLError, TimeoutError) as err:
        st.error(f"Cannot load messages: {err}")
        st.stop()

    for msg in messages:
        role = "assistant" if msg.get("role") == "assistant" else "user"
        with st.chat_message(role):
            st.markdown(msg.get("content", ""))

    user_input = st.chat_input("Send a message")
    if user_input:
        with st.chat_message("user"):
            st.markdown(user_input)
        try:
            result = send_message(
                session_id=session_id,
                message=user_input,
                api_base_url=st.session_state.api_base_url,
            )
            if result.get("status") != "ok":
                st.error(result.get("reason", "Chat request failed"))
            st.rerun()
        except (URLError, TimeoutError) as err:
            st.error(f"Message failed: {err}")


if __name__ == "__main__":
    app()
