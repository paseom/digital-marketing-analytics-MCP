"""
Marketing Analytics Chat — Streamlit frontend

Flow:
  User types a question
    -> Gemini API (with the MCP server attached as a tool via a live session)
    -> Gemini decides whether to call a tool (fetch_campaigns, generate_report, etc.)
    -> Tool result comes back as JSON, Gemini writes a natural-language answer
    -> We show ONLY the natural-language answer in the chat bubble
    -> If the tool result looks tabular, we also render it as a table/chart
       below the answer (never as raw JSON)
"""

import asyncio
import concurrent.futures
import json
import os

import pandas as pd
import streamlit as st
from google import genai
from google.genai import types
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# --- Config ---
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY"))
MCP_SERVER_URL = st.secrets.get("MCP_SERVER_URL", os.environ.get("MCP_SERVER_URL"))
GEMINI_MODEL = "gemini-2.5-flash"

st.set_page_config(page_title="Marketing Analytics Chat", page_icon="📊", layout="centered")
st.title("📊 Marketing Analytics Chat")
st.caption("Tanya soal performa campaign — data langsung dari Google Ads.")

if not GEMINI_API_KEY or not MCP_SERVER_URL:
    st.error("GEMINI_API_KEY atau MCP_SERVER_URL belum diset di Secrets. Cek Settings > Secrets.")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []  # each item: {"role": ..., "text": ..., "table": df_or_None}


def flatten_exceptions(exc) -> list[str]:
    """Recursively unwrap nested ExceptionGroups to find the real root-cause errors."""
    if isinstance(exc, BaseExceptionGroup):
        result = []
        for sub in exc.exceptions:
            result.extend(flatten_exceptions(sub))
        return result
    return [f"{type(exc).__name__}: {exc}"]


def try_extract_table(tool_response_text: str) -> pd.DataFrame | None:
    """Try to turn a tool's JSON response into a clean DataFrame for display.
    Returns None if it doesn't look tabular — caller just shows text then."""
    try:
        data = json.loads(tool_response_text)
    except (json.JSONDecodeError, TypeError):
        return None

    # A list of records (e.g. fetch_campaigns() -> List[Campaign])
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return pd.DataFrame(data)

    # A single flat dict of metrics (e.g. generate_report()/fetch_campaign_metrics())
    if isinstance(data, dict) and all(not isinstance(v, (dict, list)) for v in data.values()):
        return pd.DataFrame([data])

    return None


async def ask_gemini(question: str, history: list):
    """Connect to the MCP server for this turn, ask Gemini, return (answer_text, table_or_None)."""
    client = genai.Client(api_key=GEMINI_API_KEY)

    async with streamablehttp_client(MCP_SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            contents = history + [{"role": "user", "parts": [{"text": question}]}]

            response = await client.aio.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    tools=[session],
                    temperature=0.2,
                ),
            )

            answer_text = response.text or "(tidak ada jawaban)"

            # Pull the raw tool result (if any) from the automatic function-calling
            # history, so we can render it as a table without showing it as JSON text.
            table = None
            fc_history = getattr(response, "automatic_function_calling_history", None) or []
            for entry in fc_history:
                parts = getattr(entry, "parts", None) or []
                for part in parts:
                    fn_response = getattr(part, "function_response", None)
                    if fn_response and getattr(fn_response, "response", None):
                        raw = fn_response.response
                        raw_text = raw if isinstance(raw, str) else json.dumps(raw)
                        candidate = try_extract_table(raw_text)
                        if candidate is not None:
                            table = candidate  # keep the last tabular result

            return answer_text, table


def run_ask_gemini_isolated(question: str, history: list):
    """Run ask_gemini() in a separate thread with its own fresh event loop.
    This avoids conflicts with Streamlit's own event loop/threading model,
    which is what causes the 'cannot pickle _asyncio.Future' error when
    calling asyncio.run() directly inside a Streamlit script on cloud hosts."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, ask_gemini(question, history))
        return future.result()


# --- Render existing chat history ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["text"])
        if msg.get("table") is not None:
            df = msg["table"]
            st.dataframe(df, use_container_width=True)
            numeric_cols = df.select_dtypes(include="number").columns
            if len(numeric_cols) > 0 and len(df) > 1:
                st.bar_chart(df.set_index(df.columns[0])[numeric_cols])

# --- Chat input ---
question = st.chat_input("Contoh: gimana performa campaign bulan ini?")
if question:
    st.session_state.messages.append({"role": "user", "text": question, "table": None})
    with st.chat_message("user"):
        st.markdown(question)

    # Build history in Gemini's expected format from prior turns
    history = [
        {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["text"]}]}
        for m in st.session_state.messages[:-1]
    ]

    with st.chat_message("assistant"):
        with st.spinner("Mengambil data..."):
            try:
                answer_text, table = run_ask_gemini_isolated(question, history)
            except* Exception as eg:
                # Recursively unwrap nested ExceptionGroups (streamablehttp_client
                # and ClientSession each run their own TaskGroup) to see the
                # actual root-cause error instead of the generic wrapper message.
                sub_errors = "; ".join(flatten_exceptions(eg))
                answer_text, table = f"Terjadi error: {sub_errors}", None

        st.markdown(answer_text)
        if table is not None:
            st.dataframe(table, use_container_width=True)
            numeric_cols = table.select_dtypes(include="number").columns
            if len(numeric_cols) > 0 and len(table) > 1:
                st.bar_chart(table.set_index(table.columns[0])[numeric_cols])

    st.session_state.messages.append({"role": "assistant", "text": answer_text, "table": table})