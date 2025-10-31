import os
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from question_manager import QuestionManager

app = Flask(__name__, template_folder="templates", static_folder="static")

# Enable CORS for local development (relaxed; restrict as needed later)
CORS(app, resources={r"/*": {"origins": "*"}})


@app.route("/")
def index():
    """Serve the main game page."""
    return render_template("index.html")


# Instantiate a single QuestionManager for the running app
# Resolve questions.txt relative to this file so CWD won't break lookup
questions_file = os.path.join(os.path.dirname(__file__), "questions.txt")
question_manager = QuestionManager(file_path=questions_file)


@app.route("/api/question", methods=["GET"])
def api_get_question():
    """Return a random unused question as JSON."""
    try:
        q = question_manager.get_random_question()
        return jsonify(q), 200
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 500
    except ValueError as e:
        # No more questions available or empty file
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": "Internal server error", "detail": str(e)}), 500


@app.route("/api/validate", methods=["POST"])
def api_validate():
    """Validate an answer for a given question id.

    Expected JSON: {"question_id": "<stable id>", "answer": "<string>"}
    Returns: {"correct": bool}
    """
    try:
        payload = request.get_json(force=True)
        if not payload:
            return jsonify({"error": "Missing JSON payload"}), 400

        question_id = payload.get("question_id")
        answer = payload.get("answer")

        if question_id is None or answer is None:
            return jsonify({"error": "Both 'question_id' and 'answer' are required"}), 400

        try:
            # question_id is a stable hex string id; accept ints/strings but use str()
            correct = question_manager.validate_answer(str(question_id), answer)
        except KeyError as ke:
            return jsonify({"error": str(ke)}), 400
        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400

        return jsonify({"correct": bool(correct)}), 200
    except Exception as e:
        return jsonify({"error": "Internal server error", "detail": str(e)}), 500


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """Clear the used-questions cache and return a success message."""
    try:
        question_manager.clear_cache()
        return jsonify({"message": "Cache cleared successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Could not clear cache", "detail": str(e)}), 500


if __name__ == "__main__":
    # Run development server
    app.run(host="127.0.0.1", port=5000, debug=True)
