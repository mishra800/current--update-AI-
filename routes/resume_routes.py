import os
import re
from typing import List, Tuple
from flask import Blueprint, request, jsonify
import numpy as np

# Text extraction libs
from pdfminer.high_level import extract_text as extract_text_pdf
import docx2txt

# SentenceTransformers
from sentence_transformers import SentenceTransformer

# Optional spaCy (for NER)
import spacy

# ----------------- Lazy-loaded models -----------------
_MODEL = None
_NLP = None

def _get_model():
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _MODEL

def _get_nlp():
    global _NLP
    if _NLP is None:
        try:
            _NLP = spacy.load("en_core_web_sm")
        except Exception:
            _NLP = None
    return _NLP

# ----------------- Common skills -----------------
COMMON_SKILLS = [
    "python","java","javascript","react","node","sql","postgresql","docker",
    "aws","azure","git","html","css","c++","c#","tensorflow","pytorch","nlp",
    "machine learning","data analysis","excel","tableau","power bi","linux"
]

# ----------------- Resume logic -----------------
def extract_text_from_file(filepath: str) -> str:
    lower = filepath.lower()
    if lower.endswith(".pdf"):
        try:
            text = extract_text_pdf(filepath) or ""
        except Exception:
            text = _fallback_pdf_text(filepath)
    elif lower.endswith(".docx") or lower.endswith(".doc"):
        try:
            text = docx2txt.process(filepath) or ""
        except Exception:
            text = ""
    elif lower.endswith(".txt"):
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    else:
        text = ""
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def _fallback_pdf_text(filepath):
    try:
        with open(filepath, "rb") as f:
            b = f.read()
            return b.decode('utf-8', errors='ignore')
    except Exception:
        return ""

def extract_skills(text: str, custom_skill_list: List[str] = None) -> List[str]:
    text_lower = text.lower()
    skills = set()
    full_list = COMMON_SKILLS.copy()
    if custom_skill_list:
        full_list = list(set(full_list + custom_skill_list))
    for skill in full_list:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, text_lower):
            skills.add(skill)
    nlp = _get_nlp()
    if nlp:
        doc = nlp(text[:10000])
        for ent in doc.ents:
            if ent.label_ in ("ORG","PRODUCT","WORK_OF_ART","TECH"):
                s = ent.text.strip().lower()
                if len(s) > 1 and s not in skills and len(s.split()) <= 3:
                    skills.add(s)
    return sorted(list(skills))

def embed_text(text: str):
    model = _get_model()
    return model.encode(text, show_progress_bar=False, convert_to_numpy=True)

def cosine_similarity(vec_a, vec_b):
    a = np.array(vec_a, dtype=float)
    b = np.array(vec_b, dtype=float)
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def score_resume_vs_job(resume_text: str, job_description: str) -> Tuple[float, List[float]]:
    model = _get_model()
    emb_resume = model.encode(resume_text, show_progress_bar=False, convert_to_numpy=True)
    emb_job = model.encode(job_description, show_progress_bar=False, convert_to_numpy=True)
    sim = cosine_similarity(emb_resume, emb_job)
    sim = max(0.0, min(1.0, sim))
    return sim, emb_resume.tolist()

# ----------------- Flask Blueprint -----------------
resume_bp = Blueprint("resume_bp", __name__, url_prefix="/resume")

@resume_bp.route("/extract_skills", methods=["POST"])
def extract_resume_skills():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file provided"}), 400

    filepath = f"./temp_{file.filename}"
    file.save(filepath)
    text = extract_text_from_file(filepath)
    skills = extract_skills(text)
    os.remove(filepath)  # cleanup temp file
    return jsonify({"skills": skills})

@resume_bp.route("/score", methods=["POST"])
def score_resume():
    data = request.json
    resume_text = data.get("resume_text", "")
    job_desc = data.get("job_description", "")
    if not resume_text or not job_desc:
        return jsonify({"error": "Missing resume_text or job_description"}), 400

    score, _ = score_resume_vs_job(resume_text, job_desc)
    return jsonify({"score": score})
