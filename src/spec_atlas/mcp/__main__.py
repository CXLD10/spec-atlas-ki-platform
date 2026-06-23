"""Entry point for ``uvx spec-atlas-mcp`` / ``python -m spec_atlas.mcp``.

Builds a real SpecAtlasMCPServer over configured DB sessions and runs it on
stdio (the MCP transport expected by Claude Desktop and MCP-compatible agents).

Environment variables (via .env or shell):
  ANALYSIS_DB_URL  — PostgreSQL DSN for the Analysis DB
  SPEC_DB_URL      — PostgreSQL DSN for the Spec DB
  LLM_PROVIDER     — "fake" (default) | "gemini" | "groq"
  EMBED_PROVIDER   — "fake" (default) | "fastembed"
"""

from __future__ import annotations

import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("spec_atlas.mcp")


def main() -> None:
    """Build MCPHandlers over real sessions and run the MCP server."""
    from spec_atlas.config import get_settings
    from spec_atlas.db import analysis_session as make_analysis_session
    from spec_atlas.db import spec_session as make_spec_session
    from spec_atlas.embed import get_embedding_provider
    from spec_atlas.llm import get_llm_provider
    from spec_atlas.mcp.handlers import MCPHandlers
    from spec_atlas.mcp.server import SpecAtlasMCPServer

    settings = get_settings()

    a_factory = make_analysis_session(settings) if settings.analysis_db_url else None
    s_factory = make_spec_session(settings) if settings.spec_db_url else None

    a_session = a_factory() if a_factory else None
    s_session = s_factory() if s_factory else None

    if a_session is None:
        logger.warning(
            "ANALYSIS_DB_URL not set — MCP tools will return errors for DB queries. "
            "Set the env var to enable full functionality."
        )

    embed = get_embedding_provider(settings)
    llm = get_llm_provider(settings)

    handlers = MCPHandlers(s_session, a_session, embed, llm)
    server = SpecAtlasMCPServer(handlers=handlers)

    logger.info("spec-atlas-mcp starting (stdio transport)")
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
