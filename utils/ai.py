import json
import google.generativeai as genai
from config import Config
 
_configured = False
 
 
def _ensure_configured():
    global _configured
    if not _configured:
        if not Config.OPENAI_API_KEY:
            return False
        genai.configure(api_key=Config.OPENAI_API_KEY)
        _configured = True
    return True
 
 
NO_KEY_MESSAGE = (
    "The AI features need a Gemini API key. Add OPENAI_API_KEY to your .env file and restart the app."
)
 
 
def _get_model():
    # Gemini model name, set in config.py / .env as OPENAI_MODEL, e.g. "gemini-3.6-flash"
    return genai.GenerativeModel(Config.OPENAI_MODEL)
 
 
def _history_to_gemini(chat_history, limit):
    """Convert [{'role': 'user'|'assistant', 'message': str}, ...] into Gemini's
    [{'role': 'user'|'model', 'parts': [str]}, ...] format."""
    converted = []
    for turn in chat_history[-limit:]:
        role = "model" if turn["role"] == "assistant" else "user"
        converted.append({"role": role, "parts": [turn["message"]]})
    return converted
 
 
def ai_teacher_reply(student_name, subject_hint, chat_history):
    """chat_history: list of {'role': 'user'|'assistant', 'message': str}"""
    if not _ensure_configured():
        return NO_KEY_MESSAGE
 
    system_prompt = (
        f"You are a patient, encouraging AI teacher helping a student named {student_name}. "
        "Explain concepts step by step, use simple language and short paragraphs, ask short "
        "check-in questions to confirm understanding, and use analogies where helpful. "
        "When explaining something visual (math steps, diagrams, processes), describe it as "
        "a numbered list of steps that could be drawn on a whiteboard."
    )
    model = genai.GenerativeModel(Config.OPENAI_MODEL, system_instruction=system_prompt)
    history = _history_to_gemini(chat_history[:-1], 20) if chat_history else []
    chat = model.start_chat(history=history)
 
    last_message = chat_history[-1]["message"] if chat_history else ""
    response = chat.send_message(last_message)
    return response.text
 
 
def dashboard_chatbot_reply(user_context, chat_history, user_message):
    """General assistant available on every dashboard (admin/principal/student/parent)."""
    if not _ensure_configured():
        return NO_KEY_MESSAGE
 
    system_prompt = (
        "You are the support chatbot embedded in a school management dashboard. "
        f"Here is context about who you're talking to: {user_context}. "
        "Answer questions about attendance, results, and how to use the platform. "
        "Be concise and friendly."
    )
    model = genai.GenerativeModel(Config.OPENAI_MODEL, system_instruction=system_prompt)
    history = _history_to_gemini(chat_history, 10)
    chat = model.start_chat(history=history)
 
    response = chat.send_message(user_message)
    return response.text
 
 
def generate_exam_questions(subject, topic, difficulty, num_questions):
    """Returns a list of dicts: {question, options:[...], correct_answer, explanation}"""
    if not _ensure_configured():
        # Fallback placeholder so the flow still works without a key configured yet.
        return [
            {
                "question": f"[Add OPENAI_API_KEY to generate real questions] Sample question {i+1} on {topic or subject}?",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_answer": "Option A",
                "explanation": "Placeholder — connect your Gemini API key to generate real exam content.",
            }
            for i in range(num_questions)
        ]
 
    prompt = (
        "You are an exam-writing assistant. Respond with JSON only, no markdown fences, no extra text.\n\n"
        f"Create {num_questions} multiple-choice exam questions for the subject '{subject}'"
        f"{' on the topic ' + topic if topic else ''}, at {difficulty} difficulty. "
        "Return ONLY valid JSON: a list of objects with keys "
        "'question', 'options' (list of 4 strings), 'correct_answer' (must match one option exactly), "
        "and 'explanation' (1-2 sentences)."
    )
    model = _get_model()
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(temperature=0.5),
    )
    raw = response.text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return [{"question": "The AI response could not be parsed. Please try creating the exam again.",
                  "options": ["Retry", "Retry", "Retry", "Retry"],
                  "correct_answer": "Retry", "explanation": ""}]
 
 
def grade_exam(questions, answers):
    """questions: list from generate_exam_questions. answers: dict {index(str): chosen_option}
    Objective grading (exact match) plus a short AI feedback summary."""
    correct_count = 0
    for i, q in enumerate(questions):
        chosen = answers.get(str(i))
        if chosen == q.get("correct_answer"):
            correct_count += 1
 
    max_score = len(questions)
    score = correct_count
 
    if not _ensure_configured():
        feedback = f"Scored {score}/{max_score}. Add a Gemini API key for personalized AI feedback."
        return score, max_score, feedback
 
    summary_input = json.dumps({
        "score": score, "max_score": max_score,
        "missed_questions": [q["question"] for i, q in enumerate(questions) if answers.get(str(i)) != q.get("correct_answer")],
    })
    prompt = (
        "You are an encouraging teacher giving brief exam feedback (3-4 sentences), "
        "highlighting what to review next based on missed questions.\n\n"
        f"{summary_input}"
    )
    model = _get_model()
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(temperature=0.5),
    )
    feedback = response.text
    return score, max_score, feedback
 