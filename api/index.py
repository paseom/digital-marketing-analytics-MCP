"""
Vercel entrypoint for the MCP server.

This file doesn't redefine any tools/logic — it just takes the `mcp` object
already built in marketing_analytics/server.py and exposes it as a
Streamable HTTP ASGI app that Vercel's Python runtime can serve.

Resulting public URL (after deploy): https://<your-project>.vercel.app/api/mcp
"""

import os
import sys

# Make sure the project root is importable when running under Vercel's runtime.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from marketing_analytics.server import mcp

# streamable_http_app() returns a standard ASGI app — Vercel's Python
# runtime knows how to serve this directly.
app = mcp.streamable_http_app(path="/")
