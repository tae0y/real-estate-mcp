from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

mcp = FastMCP("real-estate")
