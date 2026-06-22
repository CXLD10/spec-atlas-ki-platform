# Wireframes

ASCII layout sketches for each page in scope. These describe structure and hierarchy, not pixel-exact spacing — defer to `DESIGN-TOKENS.md` for actual sizing, and the prototype for the Landing page's exact visual treatment.

---

## Landing (`/`)

```
┌──────────────────────────────────────────────────────────────────┐
│ ◆ SPEC·ATLAS                              Docs  MCP  GitHub  ◐  │ ← top bar, persistent
├──────────────────────────────────────────────────────────────────┤
│  L1 ●──── HUD (appears only once          ┌──────────────────┐  │
│  L2 ○      build is triggered, fixed       │  ◆ Grounded       │  │ ← Q&A dock (appears
│  L3 ○      left, vertically centered)      │    Answer         │  │   after build, fixed
│  L4 ○                                      │  "How does..."    │  │   right)
│                                             │  Authentication   │  │
│              [canvas — graph build         │  is handled in... │  │
│               renders here when active,    │  ◆auth/tok.py:24  │  │
│               otherwise fully calm/blank]  │  ─────────────    │  │
│                                             │  CONFIDENCE ▓▓▓░  │  │
│                  SPEC·ATLAS                └──────────────────┘  │
│            Your codebase, understood.                            │
│                                                                    │
│     Spec-Atlas maps any repository into a living knowledge        │
│     graph, generates grounded specs with an LLM...                │
│                                                                    │
│         ┌────────────────────────────────────────┐                │
│         │ ❯ github.com/your-org/your-repo  [Index repo] │           │
│         └────────────────────────────────────────┘                │
│             No repo handy? Watch a live index →                   │
│                                                                    │
│                      ↓ watch it build                              │
│                                                          [↻ Replay]│ ← bottom-right,
└──────────────────────────────────────────────────────────────────┘   only after a run
```

---

## Index Progress (`/index/:jobId`)

```
┌──────────────────────────────────────────────────────────────────┐
│ ◆ SPEC·ATLAS                                              ◐      │
├──────────────────────────────────────────────────────────────────┤
│  L1 ●  Code Graph        tree-sitter → symbols+edges              │
│  L2 ○  Specify           LLM → grounded specs                     │
│  L3 ○  Spec Graph        linked from real edges                   │
│  L4 ○  Group Tree        summaries + embeddings                   │
│                                                                    │
│              [same GraphScene canvas, now driven by                │
│               REAL backend progress events (Phase 6c) or           │
│               polled status percentage (interim, 6a/6b)]           │
│                                                                    │
│                   Indexing github.com/org/repo                    │
│                       ████████░░░░░░░░  42%                       │
└──────────────────────────────────────────────────────────────────┘
On completion → auto-redirect to /repo/:repoId/ask
On error → system-voice message + "Try a different repo" action, no raw stack trace
```

---

## Ask (`/repo/:repoId/ask`)

```
┌──────────────────────────────────────────────────────────────────┐
│ ◆ SPEC·ATLAS    Ask · Explore                              ◐     │ ← secondary nav
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│   ┌────────────────────────────────────────────────────────┐     │
│   │ ❯ Ask a question about this repository...        [Ask] │     │
│   └────────────────────────────────────────────────────────┘     │
│                                                                    │
│   ┌──────────────────────────────────────────────────────────┐   │
│   │ ◆ Grounded Answer                                          │   │
│   │ ┌──────────────────────────────────────────────────────┐  │   │
│   │ │ How does authentication work?                         │  │   │
│   │ └──────────────────────────────────────────────────────┘  │   │
│   │                                                              │   │
│   │ Authentication is handled in the ◆auth/tokens.py:24 module. │   │
│   │ Login flows through ◆auth/session.py:88, which validates   │   │
│   │ credentials and issues a signed token.                     │   │
│   │                                                              │   │
│   │ CONFIDENCE ▓▓▓▓▓▓▓▓▓░  92%                                  │   │
│   └──────────────────────────────────────────────────────────┘   │
│                                                                    │
│   [clicking a ◆ chip opens a code-snippet panel below or as a    │
│    slide-over — exact treatment is a Phase 6d design-review call] │
└──────────────────────────────────────────────────────────────────┘
```

---

## Explore (`/repo/:repoId/explore`)

```
┌──────────────────────────────────────────────────────────────────┐
│ ◆ SPEC·ATLAS    Ask · Explore                              ◐     │
├──────────────────────────────────────────────────────────────────┤
│ ┌─────────────┐  auth / tokens                          [stale●] │ ← breadcrumb + status
│ │ ▾ auth      │  ──────────────────────────────────────────────  │   badge (uses --l3
│ │   ▸ tokens  │  ## Auth · Tokens                                │   for stale per
│ │   ▸ session │  Manages signed token issuance and validation    │   DESIGN-TOKENS.md)
│ │ ▸ api       │  for user sessions. ◆auth/tokens.py:1-40          │
│ │ ▸ db        │                                                   │
│ │ ▸ utils     │  Member specs                                    │
│ │             │  • TokenManager.issue()      [verified]          │
│ │ (GroupTree) │  • TokenManager.validate()   [draft]              │
│ └─────────────┘                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Spec Detail (`/repo/:repoId/explore/specs/:ref`)

```
┌──────────────────────────────────────────────────────────────────┐
│ ◆ SPEC·ATLAS    Ask · Explore                              ◐     │
├──────────────────────────────────────────────────────────────────┤
│ ← auth / tokens                          TokenManager.issue() [verified]│
│ ──────────────────────────────────────────────────────────────── │
│ PURPOSE                                                           │
│ Issues a signed session token after credential validation.        │
│ ◆auth/tokens.py:24                                                 │
│                                                                    │
│ INPUTS                          OUTPUTS                           │
│ • user_id: str                  • token: str                     │
│ • scopes: list[str]              • expires_at: datetime            │
│                                                                    │
│ DEPENDENCIES        INVARIANTS                                    │
│ • auth/session.py   • token must be signed with current key       │
│                        ◆auth/tokens.py:31                          │
│                                                                    │
│ SIDE EFFECTS                    FAILURE MODES                     │
│ • writes audit log entry         • raises on expired signing key  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Layout notes that apply across all pages

- All pages sit on the same `AmbientGrid` faint background (the static grid, NOT the canvas node scene — that only renders on Landing/IndexProgress where the build animation is relevant).
- Top bar height and brand mark treatment identical everywhere — this is the one piece of chrome a user sees on every page, so it must never visually shift between pages.
- Mobile: HUD hides (per the prototype's existing media query), Q&A dock repositions to bottom-center full-width, GroupTree collapses into a top dropdown/drawer rather than a persistent sidebar on Explore.
