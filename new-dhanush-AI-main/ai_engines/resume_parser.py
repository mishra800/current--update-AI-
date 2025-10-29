import io
import json
import re
from typing import Tuple, List
import numpy as np

# Text extraction libs
from pdfminer.high_level import extract_text as extract_text_pdf
import docx2txt

# SentenceTransformers
from sentence_transformers import SentenceTransformer, util

# Optional spaCy (for NER)
import spacy

# load models lazily (costly)
_MODEL = None
_NLP = None

# small skills list - extend this for your domain
COMMON_SKILLS = [
    "python","java","javascript","react","node","sql","postgresql","docker",
    "aws","azure","git","html","css","c++","c#","tensorflow","pytorch","nlp",
    "machine learning","data analysis","excel","tableau","power bi","linux"
]

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

# ---------- Extraction ----------
def extract_text_from_file(filepath: str) -> str:
    """
    Accepts path to .pdf or .docx (or .txt). Returns plain text.
    """
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
    # Basic cleaning
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def _fallback_pdf_text(filepath):
    # minimal fallback (very small)
    try:
        with open(filepath, "rb") as f:
            b = f.read()
            # crude fallback - decode ignoring errors
            return b.decode('utf-8', errors='ignore')
    except Exception:
        return ""

# ---------- Skill extraction ----------
def extract_skills(text: str, custom_skill_list: List[str] = None) -> List[str]:
    text_lower = text.lower()
    skills = set()
    full_list = COMMON_SKILLS.copy()
    if custom_skill_list:
        full_list = list(set(full_list + custom_skill_list))
    # simple keyword matching (word boundaries)
    for skill in full_list:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, text_lower):
            skills.add(skill)
    # try some NER-based detection for ORG/TECH entities if spacy available
    nlp = _get_nlp()
    if nlp:
        doc = nlp(text[:10000])  # limit to first chunk for speed
        for ent in doc.ents:
            if ent.label_ in ("ORG","PRODUCT","WORK_OF_ART","TECH") :
                # generic check
                s = ent.text.strip().lower()
                if len(s) > 1 and s not in skills:
                    # only add short tokens
                    if len(s.split()) <= 3:
                        skills.add(s)
    return sorted(list(skills))


# ---------- Embeddings & similarity ----------
def embed_text(text: str):
    model = _get_model()
    return model.encode(text, show_progress_bar=False, convert_to_numpy=True)

def cosine_similarity(vec_a, vec_b):
    # using sentence_transformers util.cos_sim would be fine, but implement here:
    a = np.array(vec_a, dtype=float)
    b = np.array(vec_b, dtype=float)
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def score_resume_vs_job(resume_text: str, job_description: str) -> Tuple[float, List[float]]:
    """
    Returns (score 0..1, [resume_embedding])
    """
    model = _get_model()
    # Option A: compute embeddings and cosine similarity
    emb_resume = model.encode(resume_text, show_progress_bar=False, convert_to_numpy=True)
    emb_job = model.encode(job_description, show_progress_bar=False, convert_to_numpy=True)
    sim = cosine_similarity(emb_resume, emb_job)
    # clamp to 0..1
    sim = max(0.0, min(1.0, sim))
    return sim, emb_resume.tolist()
