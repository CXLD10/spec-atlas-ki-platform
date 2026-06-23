"""Serve persisted group.md files from the durable docs store.

GET /api/docs/{repo_name}               → root group.md for the repo
GET /api/docs/{repo_name}/{group_path}  → group.md for a nested group path
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

router = APIRouter()


def _resolve_doc(settings, repo_name: str, group_path: str) -> Path:
    docs_base = Path(settings.docs_dir).resolve()
    if group_path:
        target = (docs_base / repo_name / group_path / "group.md").resolve()
    else:
        target = (docs_base / repo_name / "group.md").resolve()
    # Path-traversal guard
    try:
        target.relative_to(docs_base)
    except ValueError:
        raise HTTPException(status_code=403, detail="Forbidden")
    return target


@router.get("/api/docs/{repo_name}", response_class=PlainTextResponse)
async def get_root_group_doc(repo_name: str, request: Request) -> str:
    target = _resolve_doc(request.app.state.settings, repo_name, "")
    if not target.exists():
        raise HTTPException(status_code=404, detail="Doc not found")
    return target.read_text()


@router.get("/api/docs/{repo_name}/{group_path:path}", response_class=PlainTextResponse)
async def get_group_doc(repo_name: str, group_path: str, request: Request) -> str:
    target = _resolve_doc(request.app.state.settings, repo_name, group_path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Doc not found")
    return target.read_text()
