<!--
Guidance for AI coding agents working on the "What's The Question" repo.
Focus on concrete, discoverable patterns, commands, and file references so an agent can be immediately productive.
-->

# Copilot instructions — What's The Question

Short, actionable notes for editing and extending this Flask + static frontend trivia app.

- Project entry: `app.py` — Flask app that serves `templates/index.html` and `static/*` and exposes three JSON endpoints used by the frontend: `/api/question` (GET), `/api/validate` (POST) and `/api/reset` (POST).
- Frontend: `static/js/game.js` expects JSON shaped as: `{id: string, question: string, words: string[]}` from `/api/question`. It sends `{question_id: string, answer: string}` to `/api/validate` and expects `{correct: bool}`.

Key files to inspect when making changes
- `question_manager.py` — core logic for reading `questions.txt`, stable ids, caching, normalization, and validation. Read this before changing any question/validation behavior.
- `questions.txt` — pipe-delimited lines: `QUESTION TEXT | ANSWER`. IDs are stable SHA256 of the question text; changing question text will change IDs and will break clients relying on stored ids.
- `templates/index.html` — page layout and 10 fixed word boxes (data-position 1..10). Game UI assumes up to 10 words per question.
- `static/js/game.js` — client logic: fetch, reveal words by box position, submit answer, and simple feedback logic.
- `environment.yml` — Conda environment (Python 3.12, Flask 3.*, flask-cors 4.*). Use this to create the local dev environment.

Run / debug commands
- Create and activate Conda env:
  - `conda env create -f environment.yml`
  - `conda activate wtq`
- Start dev server (same as `Makefile` target):
  - `python app.py` (development server with `debug=True`, binds to 127.0.0.1:5000)
  - `make run` is a shortcut that runs `python app.py`.

API contract examples (important when modifying endpoints)
- GET /api/question
  - Response 200: `{ "id": "<hex>", "question": "...", "words": ["w1","w2",...] }`
  - Client truncates `words` to at most 10 entries.
- POST /api/validate
  - Request JSON: `{ "question_id": "<hex>", "answer": "<string>" }`
  - Response 200: `{ "correct": true|false }`
  - Errors: 400 for bad payload, 404 if no question, 500 on server error.
- POST /api/reset
  - Clears in-memory used-question cache (useful in testing/dev).

Important implementation details & gotchas
- Question IDs
  - Stable ID = SHA256(question text). Do not change question text lightly — IDs change and the frontend persists ids between requests.
- Question file loading
  - `QuestionManager` resolves `questions.txt` relative to its module so the working directory doesn't affect file lookup.
  - It caches parsed questions and only reloads when the file mtime changes; use `QuestionManager.force_reload()` or POST `/api/reset` in code/tests to reset caches.
- Answer normalization
  - Normalization removes accents, punctuation, lowercases, collapses whitespace, and maps common number words to digits (e.g., "eleven" -> "11"). See `_normalize_answer()` in `question_manager.py` for exact behavior. Tests and clients should expect this forgiving comparison.
- Concurrency
  - Used-question tracking is an in-memory `set()` protected by a `threading.Lock`. This is NOT shared across processes/workers — if you add multiple gunicorn workers or deployment replicas, used-question state will diverge. Use an external store (Redis) if a shared state is required.
- CORS
  - `app.py` currently enables permissive CORS for local development. If adding integrations or deploying, restrict origins.

When adding features
- If you add new API endpoints: update `static/js/game.js` examples or add a small client helper mirroring the fetch/JSON patterns used now.
- Keep the 10-box UI assumption in mind or change `templates/index.html` and `game.js` together to avoid mismatches.

Small tests and debug tips
- Use `curl`/Postman to call endpoints directly when changing validation logic. Example:
  - `curl -X POST -H 'Content-Type: application/json' -d '{"question_id":"<id>","answer":"Paris"}' http://127.0.0.1:5000/api/validate`
- To simulate an empty or changed `questions.txt` file, modify it and either restart the server or call `QuestionManager.force_reload()` in a REPL.

If something is unclear
- Ask for which part to expand: run/debug steps, tests, or an automated suite. I can also add a tiny test harness that verifies `/api/question` and `/api/validate` quickly.

Files referenced above as examples: `app.py`, `question_manager.py`, `questions.txt`, `static/js/game.js`, `templates/index.html`, `environment.yml`, `Makefile`.
