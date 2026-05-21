"""server.py - MCP stdio server exposing mutual-review tools."""
from __future__ import annotations

import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from . import reviewer

server: Server = Server("mutual-review")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="review_file",
            description=(
                "Mutual code review on a file. Claude and GPT-4o each review independently, "
                "then Claude synthesizes the findings."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute path to the file"},
                    "language": {
                        "type": "string",
                        "description": "Optional language hint (e.g. python, typescript). Auto-detected from extension if omitted.",
                    },
                    "context": {"type": "string", "description": "Optional context about the code"},
                    "synthesize": {
                        "type": "boolean",
                        "description": "Generate synthesis report (default true)",
                        "default": True,
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="review_code",
            description=(
                "Mutual code review on a code snippet. Claude and GPT-4o each review "
                "independently, then Claude synthesizes."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Code snippet to review"},
                    "language": {"type": "string", "description": "Language hint (e.g. python)"},
                    "filename": {"type": "string", "description": "Optional filename for context"},
                    "context": {"type": "string", "description": "Optional context about the code"},
                    "synthesize": {
                        "type": "boolean",
                        "description": "Generate synthesis report (default true)",
                        "default": True,
                    },
                },
                "required": ["code"],
            },
        ),
        Tool(
            name="review_diff",
            description=(
                "Mutual code review on a unified diff string. Pass the diff text directly "
                "(no git invocation is performed)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "diff": {"type": "string", "description": "Unified diff text"},
                    "context": {"type": "string", "description": "Optional context"},
                    "synthesize": {
                        "type": "boolean",
                        "description": "Generate synthesis report (default true)",
                        "default": True,
                    },
                },
                "required": ["diff"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "review_file":
            result = await asyncio.to_thread(
                reviewer.review_file,
                arguments["path"],
                arguments.get("language"),
                arguments.get("context"),
                arguments.get("synthesize", True),
            )

        elif name == "review_code":
            result = await asyncio.to_thread(
                reviewer.review_code,
                arguments["code"],
                arguments.get("language"),
                arguments.get("filename"),
                arguments.get("context"),
                arguments.get("synthesize", True),
            )

        elif name == "review_diff":
            result = await asyncio.to_thread(
                reviewer.review_diff,
                arguments["diff"],
                arguments.get("context"),
                arguments.get("synthesize", True),
            )

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        return [TextContent(type="text", text=reviewer.format_result(result))]

    except Exception as exc:
        return [TextContent(type="text", text=f"Error: {exc}")]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main_sync() -> None:
    """Entry point for the `mutual-review-mcp` console script."""
    asyncio.run(main())


if __name__ == "__main__":
    main_sync()
