document.addEventListener('DOMContentLoaded', () => {
  console.log('Game script loaded and DOM ready.');

  // Game state
  const state = {
    currentQuestion: null, // {id, question, words: []}
    revealed: new Set(), // positions (1-based) revealed
    loaded: false,
    currentMode: null, // 'free' | 'challenge' | null
  };

  const feedbackEl = document.getElementById('feedback');
  const answerInput = document.getElementById('answer-input');
  const submitBtn = document.getElementById('submit-answer');

  // Feedback timeout id to avoid race conditions when auto-clearing messages
  let feedbackTimeoutId = null;
  // Submission guard to prevent duplicate in-flight submissions
  let submitPending = false;
  // Gate auto-advance behavior behind a flag for future toggling
  const autoAdvanceEnabled = true;
  const boxes = Array.from(document.querySelectorAll('.word-box'));

  // Mode selection elements
  const modeSelectionEl = document.getElementById('mode-selection');
  const gameBoardSection = document.getElementById('game-board-section');
  const freePlayBtn = document.getElementById('free-play-btn');
  const challengeModeBtn = document.getElementById('challenge-mode-btn');

  // Helper: show feedback
  function showFeedback(message, isSuccess = false) {
    if (!feedbackEl) return;
    // Clear any previous timeout so newer messages aren't wiped early
    if (feedbackTimeoutId) {
      clearTimeout(feedbackTimeoutId);
      feedbackTimeoutId = null;
    }

    feedbackEl.textContent = String(message).toUpperCase();
    feedbackEl.classList.remove('success', 'error');
    feedbackEl.classList.add(isSuccess ? 'success' : 'error');
    // auto-clear after 4s (store id so it can be cleared by a newer message)
    feedbackTimeoutId = setTimeout(() => {
      feedbackEl.textContent = '';
      feedbackEl.classList.remove('success', 'error');
      feedbackTimeoutId = null;
    }, 4000);
  }

  // Initialize board resets visual state
  function initializeBoard(questionData) {
    state.currentQuestion = questionData;
    state.revealed.clear();
    state.loaded = true;

    // Clear boxes and set tabindex/aria
    boxes.forEach((box) => {
      const pos = Number(box.dataset.position || '0');
      const wordEl = box.querySelector('.box-word');
      wordEl.textContent = '???';
      box.classList.remove('revealed');
      box.setAttribute('aria-pressed', 'false');
      // disable box if position greater than words length
      const words = questionData.words || [];
      if (pos > words.length) {
        // Keep the box visible (always show 10 boxes). Mark as disabled so it
        // remains non-interactive. The revealed logic already prevents out-of-range reveals.
        box.setAttribute('aria-disabled', 'true');
        box.classList.add('disabled');
      } else {
        box.removeAttribute('aria-disabled');
        box.classList.remove('disabled');
      }
    });

    if (answerInput) answerInput.value = '';
    if (feedbackEl) feedbackEl.textContent = '';
  }

  // Fetch a question from backend
  async function fetchQuestion() {
    try {
      const res = await fetch('/api/question');
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        showFeedback(err.error || 'No more questions available', false);
        return;
      }

      const data = await res.json();
      // Expect {id, question, words}
      if (!data || !data.id || !Array.isArray(data.words)) {
        showFeedback('Invalid question data', false);
        return;
      }
      // Limit to at most 10 words to match fixed 10 boxes and ensure strings
      data.words = (data.words || []).slice(0, 10).map((w) => String(w));
      initializeBoard(data);
    } catch (err) {
      console.error(err);
      showFeedback('Failed to fetch question', false);
    }
  }

  // Reveal word at position (1-based)
  function revealWord(position) {
    if (!state.loaded) return;
    const pos = Number(position);
    if (isNaN(pos) || pos < 1) return;
    if (state.revealed.has(pos)) return;

    const idx = pos - 1;
    const words = state.currentQuestion.words || [];
    if (idx < 0 || idx >= words.length) return;

    const box = boxes.find((b) => Number(b.dataset.position) === pos);
    if (!box) return;

    const wordText = String(words[idx]).toUpperCase();
    const wordEl = box.querySelector('.box-word');
    wordEl.textContent = wordText;
    box.classList.add('revealed');
    box.setAttribute('aria-pressed', 'true');
    state.revealed.add(pos);
  }

  // Attach click handlers to boxes
  boxes.forEach((box) => {
    box.addEventListener('click', () => {
      const pos = box.dataset.position;
      revealWord(pos);
    });
    // allow keyboard activation
    box.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter' || ev.key === ' ') {
        ev.preventDefault();
        const pos = box.dataset.position;
        revealWord(pos);
      }
    });
  });

  // Submit answer logic, guarded to avoid duplicate submissions
  async function submitAnswer() {
    if (submitPending) return;
    if (!state.loaded || !state.currentQuestion) return;
    const userAnswer = (answerInput && answerInput.value) ? answerInput.value.trim() : '';
    if (!userAnswer) {
      showFeedback('Please enter an answer', false);
      return;
    }

    submitPending = true;
    if (submitBtn) submitBtn.disabled = true;

    try {
      const payload = { question_id: state.currentQuestion.id, answer: userAnswer };
      const res = await fetch('/api/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      // Parse response safely: try JSON, fallback to text
      let parsed = null;
      try {
        parsed = await res.json();
      } catch (e) {
        const text = await res.text().catch(() => '');
        parsed = { text };
      }

      if (!res.ok) {
        const msg = (parsed && parsed.error) ? parsed.error : (parsed && parsed.text) || 'Validation failed';
        showFeedback(msg, false);
        return;
      }

      if (parsed && parsed.correct) {
        showFeedback('Correct!', true);
        // load next question after short delay (gate behind flag)
        if (autoAdvanceEnabled) setTimeout(() => fetchQuestion(), 900);
      } else {
        showFeedback('Wrong answer, try again', false);
        if (answerInput) answerInput.value = '';
      }
    } catch (err) {
      console.error(err);
      showFeedback('Error validating answer', false);
    } finally {
      submitPending = false;
      if (submitBtn) submitBtn.disabled = false;
    }
  }

  // Wire submit button
  if (submitBtn) submitBtn.addEventListener('click', submitAnswer);

  // Allow Enter in answer input to submit
  if (answerInput) {
    answerInput.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter') {
        ev.preventDefault();
        submitAnswer();
      }
    });
  }

  // Mode selection handlers
  function startFreePlayMode() {
    state.currentMode = 'free';
    if (modeSelectionEl) modeSelectionEl.classList.add('hidden');
    if (gameBoardSection) gameBoardSection.classList.remove('hidden');
    // start gameplay
    fetchQuestion();
  }

  if (freePlayBtn) {
    freePlayBtn.addEventListener('click', (ev) => {
      ev.preventDefault();
      startFreePlayMode();
    });
  }

  if (challengeModeBtn) {
    challengeModeBtn.addEventListener('click', (ev) => {
      ev.preventDefault();
      showFeedback('Challenge mode coming soon', false);
    });
  }
});
