"""
Interview AI helpers:
- embed_text(text)
- score_answer(candidate_text, reference_text) -> 0..100
- transcribe_audio(filepath) -> text (optional; uses whisper if installed)
"""

from sentence_transformers import SentenceTransformer
import numpy as np
import math
import os

# lazy load embedding model
_EMB_MODEL = None
def _get_emb_model():
    global _EMB_MODEL
    if _EMB_MODEL is None:
        _EMB_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _EMB_MODEL

def embed_text(text):
    model = _get_emb_model()
    vec = model.encode(text, show_progress_bar=False, convert_to_numpy=True)
    return vec

def cosine_similarity(a, b):
    a = np.array(a, dtype=float)
    b = np.array(b, dtype=float)
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)

def score_answer(candidate_text: str, reference_text: str) -> float:
    """
    Returns score between 0 and 100 computed from cosine similarity and heuristics.
    If reference_text is empty, returns 0.
    """
    candidate_text = (candidate_text or "").strip()
    reference_text = (reference_text or "").strip()
    if not candidate_text:
        return 0.0
    if not reference_text:
        # No reference; fallback to length-based score (not ideal)
        length_score = min(1.0, len(candidate_text) / 300.0)  # 300 chars ~ full credit
        return round(length_score * 30.0, 2)  # give up to 30 points if no ref
    try:
        emb_model = _get_emb_model()
        a = emb_model.encode(candidate_text, show_progress_bar=False, convert_to_numpy=True)
        b = emb_model.encode(reference_text, show_progress_bar=False, convert_to_numpy=True)
        sim = cosine_similarity(a, b)  # -1..1 but close to 0..1 for SBERT
        # map sim (0..1) into 0..85 points (core content)
        core = max(0.0, min(1.0, sim)) * 85.0
        # length/coverage bonus (10 points)
        coverage = min(10.0, (len(candidate_text) / max(100.0, len(reference_text))) * 10.0)
        # brevity/clarity penalty: if too long grant small extra (up to 5)
        extra = min(5.0, max(0.0, (len(candidate_text) - len(reference_text)) / 200.0 * 5.0))
        score = core + coverage + extra
        # clamp 0..100
        score = max(0.0, min(100.0, score))
        return round(score, 2)
    except Exception:
        return 0.0

# Optional: whisper-based transcription
def transcribe_audio(filepath: str) -> str:
    """
    Uses openai/whisper (whisper package) if available to transcribe audio file.
    If whisper not installed or fails, raises ImportError or RuntimeError.
    """
    try:
        import whisper
    except Exception as e:
        raise ImportError("whisper package is not installed. Install 'whisper' to enable audio transcription.") from e

    model = whisper.load_model("small")   # choose "small" or "base" depending on compute
    # whisper expects ffmpeg installed; ensure it's available
    result = model.transcribe(filepath)
    text = result.get("text", "").strip()
    return text
