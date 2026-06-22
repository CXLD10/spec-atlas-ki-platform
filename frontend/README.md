# Spec-Atlas Frontend

React + TypeScript + Vite frontend for Spec-Atlas.

## Quick start

```bash
cd frontend
npm install
npm run dev
```

App will open at `http://localhost:5173`.

## Build

```bash
npm run build
```

## Environment

Copy `.env.example` to `.env` and configure:

```env
VITE_API_URL=http://localhost:8000
```

## Development guide

See `../docs/frontend/` for complete architecture, design, and build specifications.

- `docs/frontend/README.md` — start here
- `docs/frontend/prompts/PROMPT-01-scaffold-and-scene.md` — Phase 6a (current)
- `docs/frontend/prompts/PROMPT-02-wire-real-backend.md` — Phase 6b
- `docs/frontend/prompts/PROMPT-03-real-indexing-sse.md` — Phase 6c

## Project structure

```
src/
  app/           App shell, theme provider
  components/    React components
    scene/       GraphScene, useGraphBuild, canvas animation
    hud/         PipelineHUD (stage indicator)
    qa/          AnswerDock, CitationChip
    layout/      TopBar, ThemeToggle, AmbientGrid
  pages/         Page components (Landing, RepoAsk, etc.)
  api/           API client, React Query hooks
  styles/        Global CSS, design tokens
```

## Key constraints

- **Reduced motion:** Both CSS and canvas animations respect `prefers-reduced-motion`
- **Citations:** CitationChip component used consistently everywhere
- **Layer colors:** --l1, --l2, --l3, --l4 reserved for layer identification only
- **Accessibility:** Keyboard navigation and focus states required in each task, not deferred

## Testing

Run tests with:

```bash
npm run test
```

Follow `./.claude/skills/testing-standard` for what "tested" means.

## Deployment

Frontend deploys to Vercel (free tier). Connect repo at https://vercel.com/new.

Set `VITE_API_URL` environment variable in Vercel dashboard to your backend URL.
