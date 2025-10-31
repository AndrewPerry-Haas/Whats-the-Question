import os
import random
import threading
import hashlib
import unicodedata
import re
from typing import List, Tuple, Dict, Optional


class QuestionManager:
    """Manage questions stored in a simple pipe-delimited text file.

    File format (one per line): QUESTION TEXT | ANSWER

    Behavior and features added:
    - Resolves relative file paths against the module location so CWD doesn't
      affect file lookup.
    - Caches parsed questions in-memory and reloads only when the file mtime
      changes.
    - Uses stable IDs (SHA256 of question text) so IDs don't change when the
      file order changes.
    - Tracks used question IDs in an in-memory set protected by a threading.Lock
      (note: not safe across processes; use a shared store like Redis for that).
    - Normalizes answers for more forgiving validation (punctuation, accents,
      spacing, simple number-word mapping).
    """

    NUMBER_WORDS = {
        "zero": "0",
        "one": "1",
        "two": "2",
        "three": "3",
        "four": "4",
        "five": "5",
        "six": "6",
        "seven": "7",
        "eight": "8",
        "nine": "9",
        "ten": "10",
        "eleven": "11",
        "twelve": "12",
    }

    def __init__(self, file_path: str = "questions.txt") -> None:
        # Resolve path relative to the module file so CWD doesn't matter
        if not os.path.isabs(file_path):
            base_dir = os.path.dirname(__file__)
            file_path = os.path.join(base_dir, file_path)

        self.file_path = file_path
        self._used = set()  # set of stable ids (hex strings)
        self._lock = threading.Lock()

        # cached questions: list of dicts {id, question, answer}
        self._questions: List[Dict[str, str]] = []
        self._id_map: Dict[str, Dict[str, str]] = {}
        self._mtime: Optional[float] = None

        # initial load (will raise if missing/empty)
        self._reload_if_needed(force=True)

    def _normalize_answer(self, s: Optional[str]) -> str:
        """Normalize an answer string for forgiving comparison.

        Steps:
        - None -> empty string
        - Unicode NFKD -> strip accents
        - Lowercase
        - Replace common number words with digits
        - Remove punctuation
        - Collapse whitespace
        """
        if s is None:
            return ""

        # Normalize unicode and fold accents
        s = unicodedata.normalize("NFKD", str(s))
        s = "".join(ch for ch in s if not unicodedata.combining(ch))
        s = s.lower()

        # replace simple number words with digits
        for word, digit in self.NUMBER_WORDS.items():
            # word boundaries
            s = re.sub(rf"\b{re.escape(word)}\b", digit, s)

        # remove punctuation (keep alphanumerics and spaces)
        s = re.sub(r"[^0-9a-z\s]", "", s)

        # collapse whitespace
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def _compute_id(self, question_text: str) -> str:
        """Return a stable hex id for a question text."""
        h = hashlib.sha256()
        h.update(question_text.strip().encode("utf-8"))
        return h.hexdigest()

    def _load_questions_internal(self) -> None:
        """Load and parse the questions file into in-memory structures.

        Raises FileNotFoundError or ValueError if file missing/empty.
        """
        if not os.path.isfile(self.file_path):
            raise FileNotFoundError(f"Questions file not found: {self.file_path}")

        parsed: List[Dict[str, str]] = []
        try:
            with open(self.file_path, "r", encoding="utf-8") as fh:
                for raw in fh:
                    line = raw.strip()
                    if not line:
                        continue
                    if "|" not in line:
                        continue
                    parts = line.split("|", 1)
                    question = parts[0].strip()
                    answer = parts[1].strip()
                    if question and answer:
                        _id = self._compute_id(question)
                        parsed.append({"id": _id, "question": question, "answer": answer})
        except Exception:
            raise

        if not parsed:
            raise ValueError("No questions found in file")

        # build id map
        id_map = {rec["id"]: rec for rec in parsed}

        self._questions = parsed
        self._id_map = id_map

    def _reload_if_needed(self, force: bool = False) -> None:
        """Reload questions if file changed (or if force=True)."""
        try:
            mtime = os.path.getmtime(self.file_path)
        except OSError:
            raise FileNotFoundError(f"Questions file not found: {self.file_path}")

        if force or self._mtime is None or self._mtime != mtime:
            # reload file
            self._load_questions_internal()
            self._mtime = mtime

    def load_questions(self) -> List[Tuple[str, str]]:
        """Return list of (question, answer) tuples from the cached data."""
        self._reload_if_needed()
        return [(rec["question"], rec["answer"]) for rec in self._questions]

    def force_reload(self) -> None:
        """Force reload of the questions file (public method)."""
        self._reload_if_needed(force=True)

    def get_random_question(self) -> Dict:
        """Return a random unused question as a dict with stable id.

        Dict keys: id (str), question (str), words (List[str]).
        NOTE: intentionally does NOT include the correct answer.
        """
        self._reload_if_needed()

        # pick from those whose id not in _used
        available = [rec for rec in self._questions if rec["id"] not in self._used]
        if not available:
            raise ValueError("No more unused questions available")

        chosen = random.choice(available)

        # record usage under lock
        with self._lock:
            self._used.add(chosen["id"])

        words = chosen["question"].split()
        return {"id": chosen["id"], "question": chosen["question"], "words": words}

    def validate_answer(self, question_id: str, user_answer: str) -> bool:
        """Validate the user's answer against the stored answer for a stable id.

        Comparison is performed against normalized strings. Raises KeyError if
        the question id is unknown.
        """
        self._reload_if_needed()

        qid = str(question_id)
        if qid not in self._id_map:
            raise KeyError("Invalid question id")

        correct_answer = self._id_map[qid]["answer"]
        if user_answer is None:
            return False

        norm_correct = self._normalize_answer(correct_answer)
        norm_user = self._normalize_answer(user_answer)

        return norm_correct == norm_user

    def clear_cache(self) -> None:
        """Clear the in-memory used-questions cache (thread-safe)."""
        with self._lock:
            self._used.clear()

    def get_cache_size(self) -> int:
        """Return the number of used questions currently cached."""
        with self._lock:
            return len(self._used)


__all__ = ["QuestionManager"]
