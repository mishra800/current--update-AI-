from flask import Blueprint, request, render_template, redirect, url_for, flash, current_app, session
from database.db import db
from models.interview_model import Question, Interview, Response
from ai_engines.interview_ai import score_answer, transcribe_audio
from utils.file_utils import save_upload_file, allowed_file
import os
from datetime import datetime

interview_bp = Blueprint("interview", __name__, template_folder="../templates", static_folder="../static")

# --- Admin: create / list questions (simple)
@interview_bp.route("/questions")
def list_questions():
    qs = Question.query.order_by(Question.created_at.desc()).all()
    return render_template("interview/question_list.html", questions=qs)

@interview_bp.route("/questions/create", methods=["GET", "POST"])
def create_question():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        prompt = request.form.get("prompt", "").strip()
        ref = request.form.get("reference_answer", "").strip()
        if not title or not prompt:
            flash("Title and prompt required.", "warning")
            return redirect(url_for("interview.create_question"))
        q = Question(title=title, prompt=prompt, reference_answer=ref)
        db.session.add(q)
        db.session.commit()
        flash("Question created.", "success")
        return redirect(url_for("interview.list_questions"))
    return render_template("interview/question_create.html")

# --- Candidate: start interview
@interview_bp.route("/start", methods=["GET", "POST"])
def start_interview():
    if request.method == "POST":
        name = request.form.get("candidate_name", "").strip()
        email = request.form.get("email", "").strip()
        question_ids = request.form.getlist("question_ids")
        if not name or not question_ids:
            flash("Provide your name and choose at least one question.", "warning")
            return redirect(url_for("interview.start_interview"))

        interview = Interview(candidate_name=name, email=email)
        db.session.add(interview)
        db.session.commit()
        # store chosen question ids in session for flow
        session["interview_id"] = interview.id
        session["question_queue"] = [int(q) for q in question_ids]
        session["current_index"] = 0
        return redirect(url_for("interview.answer_question"))

    questions = Question.query.all()
    return render_template("interview/start_interview.html", questions=questions)

# --- Candidate: answer current question (text or audio)
@interview_bp.route("/answer", methods=["GET", "POST"])
def answer_question():
    interview_id = session.get("interview_id")
    queue = session.get("question_queue")
    idx = session.get("current_index", 0)
    if not interview_id or not queue:
        flash("Interview session not found. Please start interview.", "warning")
        return redirect(url_for("interview.start_interview"))

    if idx >= len(queue):
        return redirect(url_for("interview.finish_interview"))

    qid = queue[idx]
    q = Question.query.get_or_404(qid)
    if request.method == "POST":
        # either text answer or audio file
        text_answer = request.form.get("answer_text", "").strip()
        audio_file = request.files.get("answer_audio")
        audio_filename_on_disk = None
        transcribed_text = None

        if audio_file and audio_file.filename != "":
            if not allowed_file(audio_file.filename):
                flash("Audio file type not allowed. Use mp3/wav/m4a (ensure ffmpeg installed).", "danger")
                return redirect(request.url)
            # save audio
            path, original_name = save_upload_file(audio_file)
            audio_filename_on_disk = os.path.basename(path)
            # attempt transcription
            try:
                transcribed_text = transcribe_audio(path)
            except Exception as e:
                current_app.logger.exception("Transcription failed")
                flash("Audio transcription failed (Whisper not installed or error). Please answer by text.", "danger")
                return redirect(request.url)

        final_answer_text = text_answer or transcribed_text or ""
        # compute score against reference
        s = score_answer(final_answer_text, q.reference_answer or "")
        resp = Response(interview_id=interview_id, question_id=q.id,
                        answer_text=final_answer_text, audio_filename=audio_filename_on_disk, score=s)
        db.session.add(resp)
        db.session.commit()

        # move index forward
        session["current_index"] = idx + 1
        # if more questions, go to next; else finish
        if session["current_index"] < len(queue):
            return redirect(url_for("interview.answer_question"))
        else:
            return redirect(url_for("interview.finish_interview"))

    # GET - show form for question
    return render_template("interview/answer_question.html", question=q, index=idx+1, total=len(queue))

@interview_bp.route("/finish")
def finish_interview():
    interview_id = session.get("interview_id")
    if not interview_id:
        flash("Interview not found.", "warning")
        return redirect(url_for("interview.start_interview"))

    interview = Interview.query.get_or_404(interview_id)
    # compute overall score = average of response scores
    responses = Response.query.filter_by(interview_id=interview.id).all()
    if responses:
        avg = sum([r.score or 0.0 for r in responses]) / len(responses)
        interview.score = round(avg, 2)
        interview.completed_at = datetime.utcnow()
        db.session.add(interview)
        db.session.commit()

    # clear session keys
    session.pop("interview_id", None)
    session.pop("question_queue", None)
    session.pop("current_index", None)

    return render_template("interview/interview_result.html", interview=interview, responses=responses)

# --- Admin: list interviews/results
@interview_bp.route("/results")
def list_interviews():
    items = Interview.query.order_by(Interview.started_at.desc()).all()
    return render_template("interview/interview_list.html", interviews=items)

@interview_bp.route("/result/<int:interview_id>")
def view_interview(interview_id):
    interview = Interview.query.get_or_404(interview_id)
    responses = Response.query.filter_by(interview_id=interview.id).all()
    return render_template("interview/interview_detail.html", interview=interview, responses=responses)
