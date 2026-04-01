from flask import Blueprint, request, jsonify, g
from core.ai import chat_complete, get_ai_client, _openai_client_available
from core.database import get_db
from api.deps import require_auth
import json
import logging

logger = logging.getLogger(__name__)
quizzes_bp = Blueprint("quizzes", __name__)


@quizzes_bp.post("/generate")
@require_auth
def generate_quiz():
    data = request.get_json(silent=True) or {}
    topic = data.get("topic", "").strip() or request.args.get("topic", "").strip()
    difficulty = data.get("difficulty", "Intermediate").strip()  # Beginner / Intermediate / Advanced
    requested_count = data.get("question_count", request.args.get("question_count", 100))
    curriculum = data.get("curriculum", [])

    if not topic:
        return jsonify({"error": "topic is required"}), 400

    try:
        question_count = int(requested_count)
    except (TypeError, ValueError):
        question_count = 100
    question_count = max(1, min(question_count, 100))

    if not get_ai_client():
        return jsonify({"error": "AI not available (API key missing)"}), 503

    difficulty_guide = {
        "Beginner":     "Focus on fundamental concepts, definitions, and basic syntax. Avoid complex scenarios.",
        "Intermediate": "Include practical application questions, common patterns, and moderate problem-solving.",
        "Advanced":     "Focus on edge cases, architecture decisions, performance trade-offs, and expert-level knowledge.",
    }.get(difficulty, "Include a mix of conceptual and practical questions.")

    topic_hints = {
        "React": "Focus on Hooks, JSX, Virtual DOM, state management, components, and React lifecycle.",
        "SQL": "Focus on Joins, aggregations, Window Functions, Normalization, indexes (B-Trees), and querying execution.",
        "Python": "Focus on Pythons data structures (dict, set), list comprehensions, decorators, generators, and OOP.",
        "Node.js": "Focus on the Event Loop, asynchronous I/O, CommonJS/ESM, Express routing, and streams.",
        "Docker": "Focus on Dockerfiles, container lifecycles, Docker Compose, volumes, networks, and best practices.",
        "Git and GitHub": "Focus on branching, rebasing vs merging, commit history manipulation, PRs, and detached HEAD state.",
        "C++": "Focus on pointers, memory management, templates, STL, polymorphism, and copy constructors.",
        "Spring Boot": "Focus on dependency injection, annotations (@RestController, @Autowired), Spring Data JPA, and application properties.",
        "ASP.NET Core": "Focus on middleware, Entity Framework Core, Dependency Injection, MVC pattern, and Kestrel.",
        "System Design": "Focus on scalability, CAP theorem, load balancers, caching, sharding, and message queues.",
    }
    
    hint = topic_hints.get(topic, f"Focus on {topic} ecosystem, standard practices, syntax, underlying architecture, and common libraries.")

    if curriculum and isinstance(curriculum, list):
        roadmap_context = f"CRITICAL ROADMAP ALIGNMENT: The user is taking a quiz for a specific roadmap about {topic}. Base the questions heavily on these exact modules and topics: {', '.join(curriculum)}."
    else:
        roadmap_context = f"Domain Subtopic Hint: {hint}"

    try:
        # Prefer direct OpenAI when available; otherwise let `chat_complete` pick a working provider/model.
        model = "gpt-4o-mini" if _openai_client_available() else None
        prompt = (
            f'Generate exactly {question_count} multiple-choice quiz questions specifically about "{topic}" at {difficulty} level.\n'
            f'{roadmap_context}\n'
            f'Difficulty guidance: {difficulty_guide}\n'
            f'CRITICAL: Questions MUST be highly specific to {topic}. Do NOT use generic programming questions that could fit any other framework or language. If the user asks for "{topic}", test their deep knowledge of {topic} specifically.\n'
            f'Cover varied subtopics defined in the hints and avoid near-duplicate questions.\n'
            f'Respond with ONLY a valid JSON array — no markdown, no explanation.\n'
            f'Each item must have: "question" (string), "options" (array of 4 strings), "correct_index" (0-based int), "explanation" (1 sentence why the answer is correct).\n'
            f'Example: [{{"question":"...","options":["A","B","C","D"],"correct_index":2,"explanation":"..."}}]'
        )

        raw = chat_complete(
            messages=[
                {"role": "system", "content": "You are an expert quiz generator. Reply with raw JSON array only. No markdown fences."},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.3,
            max_tokens=2048,
            model=model,
        )

        clean = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        questions_data = json.loads(clean)
        return jsonify({"topic": topic, "difficulty": difficulty, "questions": questions_data})

    except Exception as e:
        logger.error(f"Quiz Gen Error: {e}")
        return jsonify({"error": "Failed to generate quiz"}), 500


@quizzes_bp.post("/submit")
@require_auth
def submit_quiz():
    data = request.get_json(silent=True) or {}
    topic = data.get("topic", "General Quiz").strip()
    score = int(data.get("score", 0))
    max_score = int(data.get("max_score", 1))
    
    xp_earned = score * 1
    passed = (score / max_score) >= 0.6 if max_score > 0 else False
    user_id = g.current_user["id"]

    db = get_db()
    with db.cursor() as cursor:
        # Save quiz result
        cursor.execute(
            "INSERT INTO quiz_results (user_id, topic, score, max_score, xp_earned, passed) VALUES (%s, %s, %s, %s, %s, %s)",
            (user_id, topic, score, max_score, xp_earned, int(passed))
        )
        
        # Update user's total XP
        cursor.execute("UPDATE users SET xp = xp + %s WHERE id = %s", (xp_earned, user_id))
        
        db.commit()

        # Fetch the updated total XP for the response
        cursor.execute("SELECT xp FROM users WHERE id = %s", (user_id,))
        total_xp = cursor.fetchone()["xp"]

    return jsonify({
        "xp_earned": xp_earned, 
        "passed": passed,
        "total_xp": total_xp
    })
