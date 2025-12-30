# Repository Guidelines

## Project Structure & Module Organization
- `backend/main.py`: Flask API that proxies Brave Search and builds infobox data.
- `frontend/`: Static HTML/CSS/JS pages (`index.html`, `results.html`, `images.html`, etc.).
- `frontend/bangs.js`: DuckDuckGo bang handling used by the UI.
- `LICENSE` and `README.md` live at repo root.

## Build, Test, and Development Commands
- `python backend/main.py`: Runs the Flask API on `http://0.0.0.0:5000` (debug mode).
- `python -m venv .venv && source .venv/bin/activate && pip install flask requests`: Minimal setup based on imports in `backend/main.py`.
- `open frontend/index.html` (or any static server): Loads the UI locally; update API endpoint in JS if you run the backend elsewhere.

## Coding Style & Naming Conventions
- Python: 4-space indentation, `snake_case` functions/variables; keep routes small and readable.
- Frontend: 4-space indentation in HTML/CSS/JS; files are lowercase (e.g., `results.html`).
- Prefer simple, explicit logic over abstractions; this repo is intentionally lightweight.

## Testing Guidelines
- No automated tests currently exist.
- Manual smoke checks:
  - Start the backend and confirm `/api/search?q=test` returns JSON.
  - Open `frontend/index.html` and verify basic search flows.

## Commit & Pull Request Guidelines
- Commit history shows short, informal messages (e.g., "fix mobile pagination layout issue").
  - Keep messages concise and descriptive; no strict convention enforced.
- PRs should include:
  - A clear summary of behavior changes.
  - Screenshots for UI changes (especially search results pages).
  - Notes about any config changes (e.g., API key handling).

## Security & Configuration Tips
- `BRAVE_SEARCH_API_KEYS` in `backend/main.py` must be set locally.
  - Never commit real API keys; use environment or local-only edits.
