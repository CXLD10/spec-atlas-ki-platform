# Information Architecture

## Site map

```
/                          Landing — intro + hero + scripted demo (the prototype, ported as-is)
/index                     Start a real index job (repo URL form)
/index/:jobId               Live index progress — GraphScene in real-data mode
/repo/:repoId               Workspace shell (redirects to /repo/:repoId/ask by default)
/repo/:repoId/ask           Q&A — the AnswerDock pattern, full-page
/repo/:repoId/explore       GroupTree + GroupDetail + interactive graph
/repo/:repoId/explore/specs/:ref   Spec detail (nested under explore, since specs are
                                     reached by browsing — there's no standalone /specs route
                                     in v1; a spec without a repo/group context to browse
                                     from isn't a navigable destination on its own)
/settings                   Theme; (later) API keys, rate-limit status — minimal in v1
```

## Navigation pattern

- **Top bar persists everywhere:** brand mark, theme toggle. On `/` it also shows marketing nav (Docs/MCP/GitHub links). Inside a `/repo/:repoId/*` workspace, those marketing links are replaced by a slim secondary nav: **Ask · Explore**.
- **No global sidebar.** The `GroupTree` is a sidebar, but it's local to the Explore page, not a persistent app-wide nav element — Ask and Explore are different enough modes that a shared sidebar would just show irrelevant content half the time.
- **Breadcrumb, not back-button reliance:** inside Explore, show the tree-path breadcrumb (e.g., `auth / tokens`) above `GroupDetail`/`SpecDetail` so users always know where they are in the hierarchy without relying on browser back.

## Why no standalone repo-switcher / dashboard in v1

The original Phase 6 plan mentioned a "dashboard of previously indexed repos" as one landing-page option, but the locked decision was the cinematic-intro-then-hero approach instead. Consequence: **v1 has no multi-repo dashboard.** A user lands on `/`, indexes a repo (or revisits one via a saved URL — `/repo/:repoId/ask` is shareable/bookmarkable), and works within that single repo's workspace. A "my indexed repos" list is a reasonable v1.1 addition once there's real usage to learn from, but it's explicitly out of scope now — don't build it speculatively.
