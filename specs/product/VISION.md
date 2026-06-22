# VISION.md — Spec-Atlas

Status: ready
> Focused sub-spec. The canonical product doc is `PRD.md`; this is the short "why".

## Problem
Understanding an unfamiliar codebase takes days; AI agents do their worst work without an accurate model of it and waste tokens re-deriving context every prompt; and answering big-picture questions by dragging dozens of raw code nodes into a model is slow and costly. Intent, contracts, and the "why" live across whole regions of code — no single node holds them.

## What Spec-Atlas is
A local-first, zero-cost, multi-language tool that builds a structural code graph (tree-sitter), uses an LLM to generate structured specs from it, links those into a spec graph, and rolls everything up into a navigable `group.md` tree. It answers questions and serves specs to coding agents over an MCP server — moving a codebase from *what it is* to *what it means*.

## Primary users
Onboarding engineers; agent-augmented developers (primary); spec-driven leads. (Personas in `PRD.md` §5.)

## Outcomes
- Grounded, cited answers about an unfamiliar repo in seconds.
- Living onboarding docs (the `group.md` tree) that can't silently rot.
- Agents that build correctly the first time against a real spec, via MCP.
- Big-picture answers with small, dense context — cheaper than raw-node RAG.

## Success criteria
See `PRD.md` §4 (index speed, citation accuracy, context/cost reduction vs. baseline, spec groundedness, $0 cost).

## Why it's hard / impressive
Multi-language program analysis + LLM-synthesized specs + a hierarchical retrieval tree that beats query-time graph traversal, with hard provenance — not a generic RAG wrapper.
