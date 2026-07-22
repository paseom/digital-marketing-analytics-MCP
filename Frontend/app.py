"""
Marketing Analytics Chat — Streamlit frontend

We do the MCP <-> Gemini tool-calling loop manually instead of relying on
google-genai's experimental "pass a live MCP session as a tool" feature,
which tries to deep-copy the session internally and crashes with
"cannot pickle '_asyncio.Future' object" on Streamlit Cloud.

Flow:
  1. Connect to the MCP server, list its tools, convert them to Gemini
     function declarations.
  2. Send the user's question + tool declarations to Gemini.
  3. If Gemini responds with a function_call, we call the MCP tool
     ourselves, send the (JSON) result back to Gemini, and repeat.
  4. Once Gemini responds with plain text, that's the final answer —
     shown alone in the chat bubble. The raw JSON from the last tool
     call is kept separately and rendered as a table/chart, never as
     visible JSON text.
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

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY"))
MCP_SERVER_URL = st.secrets.get("MCP_SERVER_URL", os.environ.get("MCP_SERVER_URL"))
GEMINI_MODEL = "gemini-2.5-flash"
MAX_TOOL_ROUNDS = 5  # safety cap on how many tool calls Gemini can chain in one turn

st.set_page_config(page_title="Marketing Analytics Chat", page_icon="📊", layout="centered")
st.title("📊 Marketing Analytics Chat")
st.caption("Tanya soal performa campaign — data langsung dari Google Ads.")

if not GEMINI_API_KEY or not MCP_SERVER_URL:
    st.error("GEMINI_API_KEY atau MCP_SERVER_URL belum diset di Secrets. Cek Settings > Secrets.")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []  # {"role", "text", "table": df_or_None}


# ---------------------------------------------------------------
# Schema conversion: MCP tools use plain JSON Schema; Gemini's
# FunctionDeclaration wants uppercase type names (STRING, OBJECT, ...).
# ---------------------------------------------------------------
def _convert_schema_types(schema):
    if not isinstance(schema, dict):
        return schema
    converted = dict(schema)
    if "type" in converted and isinstance(converted["type"], str):
        converted["type"] = converted["type"].upper()
    if "properties" in converted and isinstance(converted["properties"], dict):
        converted["properties"] = {k: _convert_schema_types(v) for k, v in converted["properties"].items()}
    if "items" in converted:
        converted["items"] = _convert_schema_types(converted["items"])
    # Gemini doesn't support JSON Schema's "additionalProperties"/"$schema" etc. — drop unknowns.
    for junk_key in ("additionalProperties", "$schema", "title"):
        converted.pop(junk_key, None)
    return converted


def mcp_tools_to_gemini_declarations(mcp_tools) -> list[types.FunctionDeclaration]:
    declarations = []
    for tool in mcp_tools:
        schema = _convert_schema_types(tool.inputSchema) if tool.inputSchema else {"type": "OBJECT", "properties": {}}
        declarations.append(
            types.FunctionDeclaration(
                name=tool.name,
                description=tool.description or "",
                parameters=schema,
            )
        )
    return declarations


def try_extract_table(raw_value) -> pd.DataFrame | None:
    """Turn a tool's JSON result into a clean DataFrame, if it looks tabular."""
    try:
        data = json.loads(raw_value) if isinstance(raw_value, str) else raw_value
    except (json.JSONDecodeError, TypeError):
        return None

    if isinstance(data, list) and data and isinstance(data[0], dict):
        return pd.DataFrame(data)
    if isinstance(data, dict) and all(not isinstance(v, (dict, list)) for v in data.values()):
        return pd.DataFrame([data])
    return None


async def ask_gemini(question: str, history: list):
    client = genai.Client(api_key=GEMINI_API_KEY)

    async with streamablehttp_client(MCP_SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_result = await session.list_tools()
            declarations = mcp_tools_to_gemini_declarations(tools_result.tools)
            gemini_tools = [types.Tool(function_declarations=declarations)]

            contents = list(history) + [{"role": "user", "parts": [{"text": question}]}]
            last_table = None

            for _ in range(MAX_TOOL_ROUNDS):
                response = await client.aio.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=contents,
                    config=types.GenerateContentConfig(tools=gemini_tools, temperature=0.2),
                )

                candidate = response.candidates[0]
                function_calls = [
                    part.function_call
                    for part in candidate.content.parts
                    if getattr(part, "function_call", None)
                ]

                if not function_calls:
                    return response.text or "(tidak ada jawaban)", last_table

                # Echo the model's function-call turn back into the conversation
                contents.append(candidate.content)

                # Execute each requested tool call against the real MCP server
                response_parts = []
                for fc in function_calls:
                    tool_result = await session.call_tool(fc.name, dict(fc.args))
                    raw_text = ""
                    for item in tool_result.content:
                        if hasattr(item, "text"):
                            raw_text += item.text

                    candidate_table = try_extract_table(raw_text)
                    if candidate_table is not None:
                        last_table = candidate_table

                    response_parts.append(
                        types.Part.from_function_response(
                            name=fc.name,
                            response={"result": raw_text},
                        )
                    )

                contents.append({"role": "user", "parts": response_parts})

            return "Maaf, terlalu banyak langkah diperlukan untuk menjawab ini.", last_table


def run_ask_gemini_isolated(question: str, history: list):
    """Run the whole async flow in a dedicated thread with its own event loop."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, ask_gemini(question, history))
        return future.result()


def flatten_exceptions(exc) -> list[str]:
    if isinstance(exc, BaseExceptionGroup):
        result = []
        for sub in exc.exceptions:
            result.extend(flatten_exceptions(sub))
        return result
    return [f"{type(exc).__name__}: {exc}"]


def render_table(df: pd.DataFrame):
    st.dataframe(df, use_container_width=True)
    numeric_cols = df.select_dtypes(include="number").columns
    if len(numeric_cols) > 0 and len(df) > 1:
        st.bar_chart(df.set_index(df.columns[0])[numeric_cols])


# --- Render chat history ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["text"])
        if msg.get("table") is not None:
            render_table(msg["table"])

# --- Chat input ---
question = st.chat_input("Contoh: gimana performa campaign bulan ini?")
if question:
    st.session_state.messages.append({"role": "user", "text": question, "table": None})
    with st.chat_message("user"):
        st.markdown(question)

    history = [
        {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["text"]}]}
        for m in st.session_state.messages[:-1]
    ]

    with st.chat_message("assistant"):
        with st.spinner("Mengambil data..."):
            try:
                answer_text, table = run_ask_gemini_isolated(question, history)
            except* Exception as eg:
                sub_errors = "; ".join(flatten_exceptions(eg))
                answer_text, table = f"Terjadi error: {sub_errors}", None

        st.markdown(answer_text)
        if table is not None:
            render_table(table)

    st.session_state.messages.append({"role": "assistant", "text": answer_text, "table": table})