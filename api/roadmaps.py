from flask import Blueprint, request, jsonify, g
from core.ai import chat_complete, get_ai_client, _openai_client_available
from core.database import get_db
from api.deps import require_auth
import json
import logging
import re

logger = logging.getLogger(__name__)
roadmaps_bp = Blueprint("roadmaps", __name__)


# ---------------------------------------------------------------------------
# Topic Validation – keeps roadmap generation scoped to study/course topics
# ---------------------------------------------------------------------------

# Keywords that strongly suggest a NON-study topic
_OFF_TOPIC_PATTERNS = re.compile(
    r"\b("
    r"recipe|cook(ing)?|food|restaurant|meal|dish|cuisine|"
    r"sport|football|cricket|soccer|basketball|tennis|baseball|hockey|golf|"
    r"politic(s|al)?|election|government|party|democrat|republican|"
    r"movie|film|actor|actress|celebrity|gossip|entertainment|"
    r"stock(s)?|crypto|bitcoin|forex|trading|invest(ment)?|"
    r"relationship|dating|love|marriage|divorce|"
    r"joke|meme|funny|humor|comedy"
    r")\b",
    re.IGNORECASE,
)

# Keywords that confirm a study/course topic (must match at least one for instant allow)
_STUDY_KEYWORDS = re.compile(
    r"\b("
    r"programming|coding|software|developer|engineer|computer|data|machine learning|ml|ai|"
    r"python|java|javascript|typescript|kotlin|swift|rust|go|c\+\+|php|ruby|scala|"
    r"web|frontend|backend|fullstack|api|database|sql|nosql|cloud|devops|docker|kubernetes|"
    r"math|mathematics|algebra|calculus|statistics|physics|chemistry|biology|science|"
    r"design|ui|ux|figma|graphic|animation|3d|blender|"
    r"network|security|cybersecurity|linux|unix|shell|bash|"
    r"android|ios|mobile|flutter|react native|"
    r"blockchain|embedded|iot|robotics|electronics|"
    r"english|language|grammar|writing|communication|"
    r"finance|accounting|economics|business|management|marketing|"
    r"course|study|learn|roadmap|skill|certification|degree|exam"
    r")\b",
    re.IGNORECASE,
)


def _is_study_topic(topic: str, model) -> tuple[bool, str]:
    """
    Two-layer validation:
    1. Fast regex pre-filter (no AI cost).
    2. Short AI classification call if the regex is inconclusive.

    Returns (is_valid: bool, reason: str).
    """
    topic_lower = topic.lower()

    # Layer 1a – instant reject if obviously off-topic
    if _OFF_TOPIC_PATTERNS.search(topic_lower):
        return False, f"'{topic}' is not a study or course topic."

    # Layer 1b – instant allow if clearly study-related
    if _STUDY_KEYWORDS.search(topic_lower):
        return True, "ok"

    # Layer 2 – ask the AI to classify (short, cheap call)
    try:
        classification_prompt = (
            f'Is "{topic}" a valid academic, programming, technology, science, language, '
            f"or professional skills topic that someone would study in a course or self-learning path? "
            f"Answer with ONLY one word: YES or NO."
        )
        answer = chat_complete(
            messages=[
                {"role": "system", "content": "You classify whether a topic is study/course-related. Reply only YES or NO."},
                {"role": "user", "content": classification_prompt},
            ],
            temperature=0.0,
            max_tokens=5,
            model=model,
        )
        if answer.strip().upper().startswith("YES"):
            return True, "ok"
        return False, f"'{topic}' is not a study or course topic."
    except Exception as e:
        logger.warning(f"Topic classification AI call failed: {e}. Defaulting to allow.")
        # Fail open – if the classifier itself errors, let the main generation proceed
        return True, "ok"


def _build_fallback_roadmap(topic: str, difficulty: str, hours_per_week: int) -> dict:
    """
    Local deterministic fallback roadmap used when AI providers fail.
    This keeps the app usable even without external API access.
    """
    base_description = f"Comprehensive {difficulty}-level roadmap for mastering {topic}."
    modules = [
        {
            "title": "Start Here",
            "accent_color": "#6C63FF",
            "topics": [
                {"title": "How the Internet works", "duration": "2h", "description": "DNS, HTTP, browsers, servers.", "key_concepts": "DNS,HTTP,HTTPS,IP,TCP"},
                {"title": "What is HTTP?", "duration": "2h", "description": "Methods, status codes, headers.", "key_concepts": "GET,POST,status codes,headers"},
                {"title": "What is a Domain Name?", "duration": "1h", "description": "TLD, registrars, DNS records.", "key_concepts": "TLD,registrar,A record,CNAME"},
                {"title": "What is Hosting?", "duration": "1h", "description": "Shared, VPS, cloud hosting.", "key_concepts": "shared,VPS,cloud,CDN"},
                {"title": "DNS & how it works", "duration": "2h", "description": "Name servers, propagation.", "key_concepts": "NS,A,MX,TTL"},
                {"title": "Browsers and how they work", "duration": "2h", "description": "Rendering engines, JS runtime.", "key_concepts": "V8,Blink,DOM,CSSOM"},
            ],
        },
        {
            "title": "HTML",
            "accent_color": "#EC4899",
            "topics": [
                {"title": "Learn the basics", "duration": "4h", "description": "Tags, elements, attributes.", "key_concepts": "tags,attributes,boilerplate"},
                {"title": "Writing Semantic HTML", "duration": "3h", "description": "Semantic tags for accessibility.", "key_concepts": "header,nav,article,section"},
                {"title": "Forms and Validations", "duration": "3h", "description": "Input types, constraints API.", "key_concepts": "input,form,required,pattern"},
                {"title": "Conventions & Best Practices", "duration": "2h", "description": "Clean, accessible markup.", "key_concepts": "indentation,aria,BEM"},
                {"title": "Accessibility", "duration": "3h", "description": "ARIA roles, screen readers.", "key_concepts": "WCAG,ARIA,alt text,contrast"},
                {"title": "SEO Basics", "duration": "2h", "description": "Meta tags, structured data.", "key_concepts": "meta,og,ld+json,canonical"},
            ],
        },
        {
            "title": "CSS",
            "accent_color": "#06B6D4",
            "topics": [
                {"title": "Learn the basics", "duration": "4h", "description": "Selectors, cascade, specificity.", "key_concepts": "selector,box model,specificity"},
                {"title": "Making Layouts", "duration": "5h", "description": "Flexbox, Grid fundamentals.", "key_concepts": "flex,grid,float,position"},
                {"title": "Responsive Design", "duration": "4h", "description": "Media queries, mobile-first.", "key_concepts": "media query,rem,vw,breakpoint"},
                {"title": "Animations", "duration": "3h", "description": "Transitions and keyframes.", "key_concepts": "transition,@keyframes,transform"},
                {"title": "CSS Variables", "duration": "2h", "description": "Custom properties.", "key_concepts": "var(),custom property,:root"},
                {"title": "Pseudo classes & elements", "duration": "2h", "description": "::before, :hover, :nth-child.", "key_concepts": "::before,::after,:hover,:focus"},
            ],
        },
        {
            "title": "JavaScript",
            "accent_color": "#F59E0B",
            "topics": [
                {"title": "Syntax & Basic Constructs", "duration": "5h", "description": "Variables, loops, functions.", "key_concepts": "let,const,function,loops"},
                {"title": "DOM Manipulation", "duration": "4h", "description": "querySelector, events.", "key_concepts": "querySelector,addEventListener,DOM"},
                {"title": "Fetch API / Ajax", "duration": "3h", "description": "Async requests, JSON.", "key_concepts": "fetch,async/await,JSON"},
                {"title": "ES6+ Features", "duration": "4h", "description": "Arrow functions, destructuring.", "key_concepts": "arrow fn,destructuring,spread"},
                {"title": "Promises & Async/Await", "duration": "3h", "description": "Asynchronous JavaScript.", "key_concepts": "Promise,async,await,.then"},
                {"title": "Closures & Scope", "duration": "3h", "description": "Lexical scope, closures.", "key_concepts": "closure,scope,hoisting,IIFE"},
                {"title": "Error Handling", "duration": "2h", "description": "try/catch, custom errors.", "key_concepts": "try,catch,Error,throw"},
                {"title": "Modules", "duration": "2h", "description": "import/export, bundlers.", "key_concepts": "import,export,ESM,CJS"},
            ],
        },
        {
            "title": "Version Control Systems",
            "accent_color": "#10B981",
            "topics": [
                {"title": "Git – the basics", "duration": "3h", "description": "init, commit, log.", "key_concepts": "init,add,commit,log"},
                {"title": "Branching & Merging", "duration": "3h", "description": "branches, merge, rebase.", "key_concepts": "branch,merge,rebase,conflict"},
                {"title": "GitHub / GitLab", "duration": "2h", "description": "Remote repos, PRs.", "key_concepts": "push,pull,PR,fork"},
                {"title": "Git Workflows", "duration": "2h", "description": "Gitflow, trunk-based.", "key_concepts": "gitflow,trunk,feature branch"},
            ],
        },
        {
            "title": "Package Managers",
            "accent_color": "#8B5CF6",
            "topics": [
                {"title": "npm", "duration": "2h", "description": "Install, scripts, lock file.", "key_concepts": "install,publish,scripts,lock"},
                {"title": "yarn", "duration": "1h", "description": "Workspaces, zero-install.", "key_concepts": "yarn add,workspaces,pnp"},
                {"title": "pnpm", "duration": "1h", "description": "Disk-efficient package manager.", "key_concepts": "pnpm add,store,monorepo"},
            ],
        },
        {
            "title": "Pick a Framework",
            "accent_color": "#F97316",
            "topics": [
                {"title": "React", "duration": "2 weeks", "description": "Components, hooks, JSX.", "key_concepts": "hooks,JSX,state,props"},
                {"title": "Vue.js", "duration": "2 weeks", "description": "Options/Composition API.", "key_concepts": "v-bind,v-model,computed"},
                {"title": "Angular", "duration": "3 weeks", "description": "Full framework, TypeScript.", "key_concepts": "modules,DI,services,RxJS"},
                {"title": "Svelte", "duration": "1 week", "description": "Compiled, no virtual DOM.", "key_concepts": "stores,reactive,$:"},
                {"title": "Solid.js", "duration": "1 week", "description": "Fine-grained reactivity.", "key_concepts": "signals,effects,JSX"},
            ],
        },
        {
            "title": "CSS Architecture",
            "accent_color": "#EF4444",
            "topics": [
                {"title": "BEM", "duration": "2h", "description": "Block Element Modifier naming.", "key_concepts": "block,element,modifier,naming"},
                {"title": "Tailwind CSS", "duration": "4h", "description": "Utility-first CSS.", "key_concepts": "utility,purge,JIT,config"},
                {"title": "CSS Modules", "duration": "2h", "description": "Scoped CSS per component.", "key_concepts": "module,composes,scoped"},
                {"title": "Sass / SCSS", "duration": "3h", "description": "Variables, mixins, nesting.", "key_concepts": "$var,@mixin,@extend,nesting"},
                {"title": "PostCSS", "duration": "1h", "description": "Transform CSS with plugins.", "key_concepts": "autoprefixer,cssnano,plugin"},
            ],
        },
        {
            "title": "Build Tools",
            "accent_color": "#14B8A6",
            "topics": [
                {"title": "Vite", "duration": "3h", "description": "Fast dev server, HMR.", "key_concepts": "HMR,ESBuild,plugin,config"},
                {"title": "Webpack", "duration": "4h", "description": "Module bundler, loaders.", "key_concepts": "loader,plugin,chunk,tree-shake"},
                {"title": "Rollup", "duration": "2h", "description": "ES module bundler.", "key_concepts": "esm,treeshake,output,plugin"},
                {"title": "esbuild", "duration": "1h", "description": "Extremely fast JS bundler.", "key_concepts": "bundle,minify,transform"},
                {"title": "Linters & Formatters", "duration": "2h", "description": "ESLint, Prettier.", "key_concepts": "ESLint,Prettier,.eslintrc"},
                {"title": "Docker basics", "duration": "3h", "description": "Containerise your app.", "key_concepts": "Dockerfile,image,container,compose"},
            ],
        },
        {
            "title": "Testing",
            "accent_color": "#3B82F6",
            "topics": [
                {"title": "Unit Testing (Vitest/Jest)", "duration": "4h", "description": "Write fast, isolated tests.", "key_concepts": "describe,it,expect,mock"},
                {"title": "Integration Testing", "duration": "3h", "description": "Test components together.", "key_concepts": "Testing Library,render,fireEvent"},
                {"title": "E2E Testing (Playwright)", "duration": "4h", "description": "Browser automation tests.", "key_concepts": "page,locator,expect,CI"},
                {"title": "Cypress", "duration": "3h", "description": "Component & E2E tests.", "key_concepts": "cy.get,cy.visit,fixture"},
            ],
        },
        {
            "title": "Web Security Basics",
            "accent_color": "#6C63FF",
            "topics": [
                {"title": "HTTPS & SSL/TLS", "duration": "2h", "description": "Certificates, handshake.", "key_concepts": "TLS,cert,HSTS,mixed content"},
                {"title": "CORS", "duration": "2h", "description": "Cross-origin resource sharing.", "key_concepts": "origin,preflight,headers,credentials"},
                {"title": "Content Security Policy", "duration": "2h", "description": "Restrict resource loading.", "key_concepts": "CSP,nonce,script-src,report"},
                {"title": "OWASP Top 10", "duration": "3h", "description": "XSS, CSRF, injection.", "key_concepts": "XSS,CSRF,SQLi,A01-A10"},
                {"title": "Authentication Strategies", "duration": "3h", "description": "JWT, OAuth, session auth.", "key_concepts": "JWT,OAuth,session,cookie"},
            ],
        },
    ]

    # Post-process fallback roadmap to add topic IDs (mock/temporary)
    for m_idx, m in enumerate(modules):
        for t_idx, t in enumerate(m.get("topics", [])):
            slug = t["title"].lower().replace(" ", "_")
            t["id"] = f"fallback_{m_idx}_{t_idx}_{slug}"

    return {
        "goal_title": f"{topic} Roadmap",
        "description": base_description,
        "hours_per_week": hours_per_week,
        "difficulty": difficulty,
        "modules": modules,
    }


@roadmaps_bp.post("/generate")
@require_auth
def generate_roadmap():
    data = request.get_json(silent=True) or {}
    topic = data.get("topic", "").strip()
    difficulty = data.get("difficulty", "Beginner").strip()

    if not topic:
        return jsonify({"error": "Target topic is required"}), 400
    if not difficulty:
        return jsonify({"error": "Intensity level is required"}), 400

    try:
        hours_per_week = int(data.get("hours_per_week", 5))
    except (ValueError, TypeError):
        return jsonify({"error": "Time commitment must be a number"}), 400

    if not (0 <= hours_per_week <= 50):
        return jsonify({"error": "Time commitment must be between 0 and 50 hours"}), 400

    if not get_ai_client():
        return jsonify({"error": "AI not available — set OPENROUTER_API_KEY or OPENAI_API_KEY in .env"}), 503

    # --- Server-side topic guard (runs before any expensive AI call) ---
    model = "gpt-4o-mini" if _openai_client_available() else None
    is_valid, reason = _is_study_topic(topic, model)
    if not is_valid:
        return jsonify({
            "error": f"Roadmap not generated: {reason} "
                     f"Please enter a study or course topic (e.g. Python, Data Science, Web Development)."
        }), 400

    # model is already set above by the topic guard

    try:
        prompt = (
            f'You are building a professional, roadmap.sh-quality learning roadmap for "{topic}" '
            f'at "{difficulty}" level for someone with {hours_per_week} hours per week. '
            f'You MUST strictly consider the "{difficulty}" level when deciding the depth and complexity of topics.\n\n'
            f'STRICT TOPIC RESTRICTION: You MUST ONLY generate roadmaps for academic, programming, technology, or professional study topics. '
            f'If the topic "{topic}" is a random name, non-academic, or completely unrelated to studying/learning, '
            f'you MUST immediately return this EXACT JSON: {{"error": "Topic is not related to study or courses."}}. Do not generate a roadmap.\n\n'
            f'STRUCTURE REQUIREMENTS (very strict – follow exactly):\n'
            f'- Generate 10 to 15 sequential MODULES. Each module = one phase of the learning journey.\n'
            f'- Each module MUST have 8 to 15 topic nodes. Topics = specific skills, tools, or concepts.\n'
            f'- Topic titles must be SPECIFIC (e.g. "React Hooks", "Flexbox", "JWT Auth") NOT generic (e.g. "Learn something").\n'
            f'- Duration should be realistic: "2h", "1 day", "3 days", "1 week".\n'
            f'- Each module gets a unique bright accent_color hex (use: #6C63FF #EC4899 #06B6D4 #10B981 #F59E0B #F97316 #8B5CF6 #EF4444 #3B82F6 #14B8A6 in rotation).\n'
            f'- goal_title = "{topic} Roadmap" (exact format).\n\n'
            f'CONTENT REQUIREMENTS:\n'
            f'- Cover: fundamentals → core tools → frameworks → advanced topics → production/career.\n'
            f'- Include real tools used in 2024/2025 industry (e.g. Vite, Bun, Playwright, Docker, etc.).\n'
            f'- For CS topics include: data structures, algorithms, system design, databases, cloud.\n\n'
            f'OUTPUT: Respond with raw JSON only. No markdown. No explanation. No ```json fences.\n'
            f'Schema: {{"goal_title":"string","description":"one sentence","modules":['
            f'{{"title":"string","accent_color":"#RRGGBB","topics":['
            f'{{"title":"string","duration":"string","description":"one sentence","key_concepts":"comma,separated"}}'
            f']}}]}}'
        )

        try:
            raw = chat_complete(
                messages=[
                    {"role": "system", "content": (
                        "You are a world-class curriculum designer and software engineer. "
                        "You create detailed, accurate, and actionable learning roadmaps. "
                        "Always reply with raw JSON only — no markdown fences, no preamble, no trailing text."
                    )},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=4096,
                model=model,
            )

            # Strip any markdown fences the model may have added anyway
            clean = raw.strip()
            # Remove opening fence (```json or ```)
            if clean.startswith("```"):
                lines = clean.split("\n")
                # drop first line (the fence line) and last line if it's a closing fence
                lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                clean = "\n".join(lines).strip()

            roadmap_data = json.loads(clean)
            
            # Check if AI rejected the topic for not being study-related
            if "error" in roadmap_data:
                return jsonify({"error": roadmap_data["error"]}), 400
                
        except Exception as e:
            logger.error(f"AI generation failed, using fallback roadmap. Error: {e}")
            roadmap_data = _build_fallback_roadmap(topic, difficulty, hours_per_week)

        # Save to database for this user (database.py has autocommit=True)
        db = get_db()
        user_id = g.current_user["id"]
        roadmap_data["source"] = "AI Generated"
        roadmap_data["is_saved"] = True   # auto-add to My Learning

        with db.cursor() as cursor:
            cursor.execute(
                "INSERT INTO roadmaps (user_id, goal_title, data) VALUES (%s, %s, %s)",
                (user_id, roadmap_data.get("goal_title", topic), json.dumps(roadmap_data))
            )
            db.commit()
            new_id = cursor.lastrowid

        # Return id as STRING — Android Moshi deserializes id field as String?
        roadmap_data["id"] = str(new_id)

        # POST-PROCESS: Add unique IDs to each topic using the new roadmap_id
        # This ensures consistency for progress tracking (topic_id = {roadmap_id}_{topic_slug})
        for module in roadmap_data.get("modules", []):
            for topic_item in module.get("topics", []):
                slug = topic_item["title"].lower().replace(" ", "_")
                topic_item["id"] = f"{new_id}_{slug}"
        
        # Update the DB record with the populated IDs
        with db.cursor() as cursor:
            cursor.execute(
                "UPDATE roadmaps SET data = %s WHERE id = %s",
                (json.dumps(roadmap_data), new_id)
            )
            db.commit()

        return jsonify(roadmap_data)

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}\nRaw AI response: {raw[:500]}")
        return jsonify({"error": "AI returned invalid JSON. Please try again."}), 500
    except Exception as e:
        logger.error(f"Roadmap Gen Error: {e}")
        return jsonify({"error": f"Failed to generate roadmap: {str(e)}"}), 500


@roadmaps_bp.get("/")
@require_auth
def get_active_roadmaps():
    db = get_db()
    user_id = g.current_user["id"]
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT id, user_id, goal_title, data, created_at "
                "FROM roadmaps WHERE user_id = %s ORDER BY created_at DESC LIMIT 100",
                (user_id,)
            )
            rows = cursor.fetchall()

        roadmaps = []
        for row in rows:
            rdata = row["data"] if isinstance(row["data"], dict) else json.loads(row["data"])
            rdata["id"] = str(row["id"])   # Always return id as string
            roadmaps.append({
                "id": str(row["id"]),
                "user_id": row["user_id"],
                "goal_title": row["goal_title"],
                "data": rdata,
                "created_at": str(row["created_at"]),
            })
        return jsonify({"roadmaps": roadmaps})

    except Exception as e:
        logger.error(f"Failed to fetch roadmaps: {e}")
        return jsonify({"error": "Database query failed"}), 500


@roadmaps_bp.put("/progress")
@require_auth
def update_topic_progress():
    topic_id = request.args.get("topic_id", "").strip()
    if not topic_id:
        return jsonify({"error": "topic_id query param is required"}), 400

    user_id = g.current_user["id"]
    xp_earned = 5

    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(
            "INSERT IGNORE INTO topic_progress (user_id, topic_id, xp_earned) VALUES (%s, %s, %s)",
            (user_id, topic_id, xp_earned),
        )
        affected = cursor.rowcount
        if affected > 0:
            cursor.execute("UPDATE users SET xp = xp + %s WHERE id = %s", (xp_earned, user_id))

        cursor.execute("SELECT xp FROM users WHERE id = %s", (user_id,))
        total_xp = cursor.fetchone()["xp"]

    return jsonify({
        "message": f"Topic '{topic_id}' marked as complete",
        "xp_earned": xp_earned if affected > 0 else 0,
        "total_xp": total_xp,
    })


@roadmaps_bp.post("/save-offline")
@require_auth
def save_offline_roadmap():
    """Saves a fully provided roadmap JSON to the DB directly (e.g. from Mock Data)."""
    user_id = g.current_user["id"]
    roadmap_data = request.get_json()
    if not roadmap_data:
        return jsonify({"error": "No roadmap data provided"}), 400

    roadmap_data["source"] = "Offline Roadmap"
    roadmap_data["is_saved"] = True

    db = get_db()
    try:
        with db.cursor() as cursor:
            # DEDUPLICATION: Check if a roadmap with this title already exists for this user
            cursor.execute(
                "SELECT id FROM roadmaps WHERE user_id = %s AND goal_title = %s",
                (user_id, roadmap_data.get("goal_title", "Offline Roadmap"))
            )
            existing = cursor.fetchone()
            
            if existing:
                # Update existing
                cursor.execute(
                    "UPDATE roadmaps SET data = %s WHERE id = %s",
                    (json.dumps(roadmap_data), existing["id"])
                )
                new_id = existing["id"]
            else:
                # Insert new
                cursor.execute(
                    "INSERT INTO roadmaps (user_id, goal_title, data) VALUES (%s, %s, %s)",
                    (user_id, roadmap_data.get("goal_title", "Offline Roadmap"), json.dumps(roadmap_data))
                )
                new_id = cursor.lastrowid
            
            db.commit()
            
        roadmap_data["id"] = str(new_id)
        return jsonify(roadmap_data)
    except Exception as e:
        logger.error(f"Failed to save offline roadmap: {e}")
        return jsonify({"error": "Failed to save offline roadmap"}), 500


@roadmaps_bp.post("/<roadmap_id>/save")
@require_auth
def save_roadmap(roadmap_id):
    """
    Saves an existing roadmap so it appears in the user's 'My Learning' section.
    We do this by appending/setting `"is_saved": true` within the JSON data column.
    """
    user_id = g.current_user["id"]
    db = get_db()
    try:
        with db.cursor() as cursor:
            # Check if it exists and belongs to the user
            cursor.execute("SELECT id FROM roadmaps WHERE id = %s AND user_id = %s", (roadmap_id, user_id))
            if not cursor.fetchone():
                return jsonify({"error": "Roadmap not found or unauthorized"}), 404
                
            cursor.execute(
                "UPDATE roadmaps SET data = JSON_SET(data, '$.is_saved', true, '$.source', COALESCE(JSON_EXTRACT(data, '$.source'), 'Explore')) WHERE id = %s AND user_id = %s",
                (roadmap_id, user_id)
            )
            db.commit()
            
        return jsonify({"message": "Roadmap saved successfully"})
    except Exception as e:
        logger.error(f"Failed to save roadmap {roadmap_id}: {e}")
        return jsonify({"error": "Database error"}), 500


@roadmaps_bp.delete("/<roadmap_id>")
@require_auth
def delete_roadmap(roadmap_id):
    """
    Deletes a roadmap.
    """
    user_id = g.current_user["id"]
    db = get_db()
    try:
        with db.cursor() as cursor:
            # Check if it exists and belongs to the user
            cursor.execute("DELETE FROM roadmaps WHERE id = %s AND user_id = %s", (roadmap_id, user_id))
            if cursor.rowcount == 0:
                return jsonify({"error": "Roadmap not found or unauthorized"}), 404
            db.commit()
            
        return jsonify({"message": "Roadmap deleted successfully"})
    except Exception as e:
        logger.error(f"Failed to delete roadmap {roadmap_id}: {e}")
        return jsonify({"error": "Database error"}), 500
