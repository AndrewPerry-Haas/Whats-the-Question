# What's The Question - Trivia Game

A simple Flask-based web app scaffold for a local trivia game. This initial setup serves a basic HTML page with linked CSS and JavaScript, ready for expanding gameplay and API endpoints.

## Setup (Conda)

Create the Conda environment from the included spec and activate it:

```bash
conda env create -f environment.yml
conda activate wtq
```

## Running the application

Start the Flask development server:

```bash
python app.py
```

Then open your browser at:

- <http://localhost:5000>

You should see the placeholder game page with a Start button.

## Project structure

- `environment.yml` — Conda environment specification (Python, Flask, flask-cors).
- `app.py` — Flask application entry point; serves the main page and configures CORS for local development.
- `templates/` — Jinja2 HTML templates rendered by Flask.
  - `templates/index.html` — Main page template for the game UI.
- `static/` — Static assets served by Flask.
  - `static/css/style.css` — Base styles and simple layout.
  - `static/js/game.js` — Placeholder client-side logic; logs and handles Start button.
- `.gitignore` — Ignore common Python and editor artifacts.

## Notes

- CORS is currently permissive for local development convenience. Tighten it before deploying.
- This project now uses Conda for dependency management. If you prefer pip, you may adapt from `environment.yml` to a `requirements.txt` as needed.
- Future phases can add API endpoints (e.g., `/api/question`) and richer frontend logic.

