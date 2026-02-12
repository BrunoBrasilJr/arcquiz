import json
import os
import random
import sqlite3
from datetime import datetime
from typing import Any, Dict, List

from flask import Flask, render_template, request, redirect, url_for, session, flash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
QUESTIONS_PATH = os.path.join(DATA_DIR, "questions.json")

# ✅ Vercel/serverless (Linux): /var/task é read-only; use /tmp para gravar
# Local (Windows/macOS): mantém o DB na raiz do projeto
def resolve_db_path() -> str:
    # Se você quiser forçar via env var no futuro:
    env_path = os.environ.get("DB_PATH")
    if env_path:
        return env_path

    # Vercel roda em Linux; /tmp é gravável
    if os.name != "nt":
        return os.path.join("/tmp", "quiz.db")

    # Local (Windows)
    return os.path.join(BASE_DIR, "quiz.db")


DB_PATH = resolve_db_path()

APP_NAME = "ArcQuiz"  # nome do produto (pode trocar)
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "arcquiz-dev-secret")


def get_db() -> sqlite3.Connection:
    # Garante que o diretório exista (por segurança)
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS highscores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                score INTEGER NOT NULL,
                total INTEGER NOT NULL,
                percent REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


# ✅ Não inicializa no import (Vercel quebra aqui). Inicializa no request.
@app.before_request
def _ensure_db_ready() -> None:
    init_db()


def load_questions() -> List[Dict[str, Any]]:
    if not os.path.exists(QUESTIONS_PATH):
        raise FileNotFoundError(f"Arquivo não encontrado: {QUESTIONS_PATH}")

    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    required = {"id", "question", "options", "answer_index", "explanation"}
    for q in data:
        if not required.issubset(q.keys()):
            missing = required - set(q.keys())
            raise ValueError(f"Pergunta inválida (faltando {missing}): {q}")

        if not isinstance(q["options"], list) or len(q["options"]) != 4:
            raise ValueError(f"Pergunta {q.get('id')} precisa ter 4 opções.")

        ai = q["answer_index"]
        if not isinstance(ai, int) or ai < 0 or ai > 3:
            raise ValueError(f"Pergunta {q.get('id')} tem answer_index inválido: {ai}")

    return data


def question_count() -> int:
    try:
        return len(load_questions())
    except Exception:
        return 0


def shuffle_question(q: Dict[str, Any]) -> Dict[str, Any]:
    options = q["options"]
    correct_idx = q["answer_index"]

    indexed = list(enumerate(options))
    random.shuffle(indexed)

    new_options = [text for _, text in indexed]
    new_correct_idx = next(i for i, (old_idx, _) in enumerate(indexed) if old_idx == correct_idx)

    shuffled = dict(q)
    shuffled["options"] = new_options
    shuffled["answer_index"] = new_correct_idx
    return shuffled


def clamp_int(value: str, default: int, min_v: int, max_v: int) -> int:
    try:
        x = int(value)
        return max(min_v, min(max_v, x))
    except Exception:
        return default


def build_quiz_session(amount: int) -> None:
    questions = load_questions()
    random.shuffle(questions)

    available = len(questions)
    amount = max(1, min(amount, available))

    selected = questions[:amount]
    prepared = [shuffle_question(q) for q in selected]

    session["quiz"] = {
        "questions": prepared,
        "idx": 0,
        "score": 0,
        "answers": [],
        "started_at": datetime.utcnow().isoformat(),
    }
    session["score_saved"] = False


def current_quiz() -> Dict[str, Any]:
    quiz = session.get("quiz")
    if not quiz or "questions" not in quiz:
        return {}
    return quiz


def grade_rank(score: int, total: int) -> Dict[str, str]:
    if total <= 0:
        return {"title": "Resultado indisponível", "msg": "Não foi possível calcular o resultado."}

    pct = score / total
    if pct == 1.0:
        return {"title": "Excelente", "msg": "Pontuação máxima. Ótimo desempenho."}
    if pct >= 0.8:
        return {"title": "Muito bom", "msg": "Desempenho consistente e acima da média."}
    if pct >= 0.6:
        return {"title": "Bom", "msg": "Bom resultado. Há espaço para evoluir."}
    if pct >= 0.4:
        return {"title": "Regular", "msg": "Você está no caminho. Continue praticando."}
    return {"title": "Iniciante", "msg": "Normal no começo. Prática traz consistência."}


@app.get("/")
def index():
    available = question_count()
    return render_template("index.html", app_name=APP_NAME, available=available)


@app.post("/start")
def start():
    available = question_count()
    if available <= 0:
        flash("Não há perguntas disponíveis. Verifique data/questions.json.", "error")
        return redirect(url_for("index"))

    name = request.form.get("name", "").strip() or "Player"
    requested_raw = request.form.get("amount", "")
    default_amount = min(10, available)

    requested = clamp_int(requested_raw, default=default_amount, min_v=1, max_v=available)

    # Se o usuário tentou pedir mais do que existe (ou mexeu no input), ajusta e avisa
    try:
        raw_int = int(requested_raw)
        if raw_int > available:
            flash(f"Quantidade ajustada para {available} (total disponível).", "warning")
    except Exception:
        pass

    session["player_name"] = name
    session["amount"] = requested

    build_quiz_session(amount=requested)
    return redirect(url_for("quiz"))


@app.get("/quiz")
def quiz():
    quiz_state = current_quiz()
    if not quiz_state:
        flash("Nenhum quiz ativo. Inicie um novo.", "warning")
        return redirect(url_for("index"))

    idx = quiz_state["idx"]
    questions = quiz_state["questions"]
    total = len(questions)

    if idx >= total:
        return redirect(url_for("result"))

    q = questions[idx]
    letters = ["A", "B", "C", "D"]
    options = list(zip(letters, q["options"]))

    return render_template(
        "quiz.html",
        app_name=APP_NAME,
        name=session.get("player_name", "Player"),
        idx=idx,
        total=total,
        question=q["question"],
        qid=q["id"],
        options=options,
    )


@app.post("/answer")
def answer():
    quiz_state = current_quiz()
    if not quiz_state:
        flash("Nenhum quiz ativo. Volte ao início.", "warning")
        return redirect(url_for("index"))

    idx = quiz_state["idx"]
    questions = quiz_state["questions"]
    total = len(questions)

    if idx >= total:
        return redirect(url_for("result"))

    chosen = (request.form.get("choice") or "").strip().upper()
    if chosen not in {"A", "B", "C", "D"}:
        flash("Selecione uma alternativa válida (A, B, C ou D).", "error")
        return redirect(url_for("quiz"))

    q = questions[idx]
    correct_letter = ["A", "B", "C", "D"][q["answer_index"]]
    is_correct = chosen == correct_letter

    if is_correct:
        quiz_state["score"] += 1

    quiz_state["answers"].append(
        {
            "id": q["id"],
            "question": q["question"],
            "chosen": chosen,
            "correct": correct_letter,
            "is_correct": is_correct,
            "explanation": q["explanation"],
        }
    )

    quiz_state["idx"] += 1
    session["quiz"] = quiz_state

    return redirect(url_for("quiz"))


@app.get("/result")
def result():
    quiz_state = current_quiz()
    if not quiz_state:
        flash("Nenhum quiz ativo. Inicie um novo.", "warning")
        return redirect(url_for("index"))

    name = session.get("player_name", "Player")
    score = int(quiz_state.get("score", 0))
    total = len(quiz_state.get("questions", []))
    percent = (score / total * 100.0) if total else 0.0
    rank = grade_rank(score, total)

    if not session.get("score_saved", False):
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO highscores (name, score, total, percent, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, score, total, float(percent), datetime.utcnow().isoformat()),
            )
            conn.commit()
        session["score_saved"] = True

    answers = quiz_state.get("answers", [])
    return render_template(
        "result.html",
        app_name=APP_NAME,
        name=name,
        score=score,
        total=total,
        percent=percent,
        rank=rank,
        answers=answers,
    )


@app.get("/highscores")
def highscores():
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT name, score, total, percent, created_at
            FROM highscores
            ORDER BY percent DESC, score DESC, created_at DESC
            LIMIT 20
            """
        ).fetchall()

    items = [
        {
            "name": r["name"],
            "score": r["score"],
            "total": r["total"],
            "percent": r["percent"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]
    return render_template("highscores.html", app_name=APP_NAME, items=items)


@app.post("/reset")
def reset():
    # Reset = novo quiz imediatamente (shuffle novo), mantendo nome e quantidade escolhida
    available = question_count()
    if available <= 0:
        session.pop("quiz", None)
        session["score_saved"] = False
        flash("Não há perguntas disponíveis. Verifique data/questions.json.", "error")
        return redirect(url_for("index"))

    amount = session.get("amount", min(10, available))
    amount = max(1, min(int(amount), available))

    build_quiz_session(amount=amount)
    flash("Novo quiz iniciado.", "success")
    return redirect(url_for("quiz"))


if __name__ == "__main__":
    app.run(debug=True)
