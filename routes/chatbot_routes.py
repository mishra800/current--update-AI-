from flask import Blueprint, render_template, request, jsonify, current_app
from ai_engines.chatbot_llm import ingest_document, retrieve_context, generate_answer, get_collection
from database.db import db
from models.chatbot_model import ChatSession, ChatMessage
from utils.file_utils import save_upload_file, allowed_file
import os, json

# ✅ Correct Blueprint Name
chatbot_bp = Blueprint("chatbot", __name__, template_folder="../templates", static_folder="../static")


@chatbot_bp.route("/chat")
def chat_ui():
    return render_template("chatbot/chatbot_ui.html")


@chatbot_bp.route("/chat/upload", methods=["POST"])
def chat_upload():
    if 'file' not in request.files:
        return jsonify({"ok": False, "error": "no_file"}), 400
    
    f = request.files['file']

    if f.filename == "":
        return jsonify({"ok": False, "error": "empty_filename"}), 400
    
    if not allowed_file(f.filename):
        return jsonify({"ok": False, "error": "extension_not_allowed"}), 400

    path, original = save_upload_file(f)
    meta = {"uploader": request.form.get("uploader", "anonymous")}
    
    result = ingest_document(path, doc_id=original, metadata=meta)
    return jsonify(result)


@chatbot_bp.route("/chat/query", methods=["POST"])
def chat_query():
    payload = request.json or {}
    question = payload.get("question", "")
    session_id = payload.get("session_id")
    top_k = int(payload.get("top_k", 4))
    use_openai = payload.get("use_openai", True)

    if not question:
        return jsonify({"ok": False, "error": "empty_question"}), 400

    # Retrieve relevant context
    context = retrieve_context(question, top_k=top_k)

    # Generate AI answer
    answer = generate_answer(question, context, use_openai=use_openai)

    # Save to DB
    if session_id:
        session = ChatSession.query.get(session_id)
    else:
        session = ChatSession()
        db.session.add(session)
        db.session.commit()

    # User message
    user_msg = ChatMessage(session_id=session.id, role="user", text=question)
    db.session.add(user_msg)

    # Assistant message
    bot_msg = ChatMessage(session_id=session.id, role="assistant", text=answer)
    db.session.add(bot_msg)

    db.session.commit()

    return jsonify({
        "ok": True,
        "answer": answer,
        "session_id": session.id,
        "context": context
    })


@chatbot_bp.route("/chat/history/<int:session_id>")
def chat_history(session_id):
    session = ChatSession.query.get_or_404(session_id)
    messages = session.messages.order_by(ChatMessage.created_at.asc()).all()

    formatted = [
        {"role": m.role, "text": m.text, "created_at": m.created_at.isoformat()}
        for m in messages
    ]

    return jsonify({"session_id": session.id, "messages": formatted})


@chatbot_bp.route("/chat/collections")
def chat_collections():
    coll = get_collection()

    try:
        stats = coll.count()
    except Exception:
        stats = None

    return jsonify({"ok": True, "collection": "hr_docs", "stats": stats})
