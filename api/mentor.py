from flask import Blueprint, request, jsonify
from core.ai import chat_complete, get_ai_client
import logging

logger = logging.getLogger(__name__)
mentor_bp = Blueprint("mentor", __name__)

# ── System prompt ─────────────────────────────────────────────────────────────

STUDY_SYSTEM_PROMPT = """You are LearnFlow AI Companion — a dedicated educational assistant built exclusively \
for the LearnFlow platform. Your ONLY purpose is to help students with:

- Programming languages (Python, JavaScript, TypeScript, Kotlin, SQL, etc.)
- Computer science concepts (data structures, algorithms, system design, etc.)
- Technology frameworks and tools (React, Node.js, Docker, etc.)
- Academic subjects related to technology and software engineering
- Learning roadmaps, study tips, and course-related guidance
- Explaining code, debugging help, and technical concepts

STRICT RULES you must NEVER break:
1. If the user's question is NOT related to studying, learning, courses, or technology topics, \
reply ONLY with: "That question is outside my area! I'm here to help with your studies and \
coursework. Feel free to ask me anything about programming, technology, or your learning path. 😊"
2. Never reveal, mention, or hint at any API keys, configuration details, internal system details, \
or how you are implemented. If asked, say: "I'm your LearnFlow AI Companion, here to help you learn!"
3. Never discuss politics, religion, relationships, entertainment gossip, or any non-academic topic.
4. Always be encouraging, concise, and student-friendly.
5. When explaining code or concepts, be clear and use examples.
"""


@mentor_bp.post("/chat")
def send_message():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    topic = data.get("topic", "General Programming").strip()
    context = data.get("context", "")

    if not message:
        return jsonify({"error": "message is required"}), 400

    if not get_ai_client():
        return jsonify({"error": "AI Companion is temporarily unavailable. Please try again later."}), 503

    try:
        system_prompt = STUDY_SYSTEM_PROMPT
        if topic and topic != "General Programming":
            system_prompt += f"\n\nThe student is currently studying: {topic}."
        if context:
            system_prompt += f"\nContext from their learning path: {context}"

        reply = chat_complete(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": message},
            ],
            temperature=0.7,
            max_tokens=512,
        )
        return jsonify({"reply": reply})

    except Exception as e:
        logger.error(f"Mentor AI Error: {e}")
        return jsonify({"error": "AI Companion is temporarily unavailable. Please try again later."}), 500


@mentor_bp.get("/history")
def get_chat_history():
    return jsonify([])
