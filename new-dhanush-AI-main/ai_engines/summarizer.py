"""
Two summarization modes:
- LLM summarizer (if OPENAI_API_KEY or other LLM configured).
- Extractive summarizer: split feedback into sentences, embed sentences with SentenceTransformer,
  compute centroid, pick top-k sentences closest to centroid as summary.
"""

from sentence_transformers import SentenceTransformer, util
import os
import math

_MODEL = None
def _get_model():
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _MODEL

def extractive_summary(text, max_sentences=3):
    if not text:
        return ""
    # split to sentences (naive)
    import re
    sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    if not sents:
        return ""
    model = _get_model()
    embeddings = model.encode(sents, convert_to_tensor=True)
    centroid = embeddings.mean(dim=0)
    cos = util.cos_sim(embeddings, centroid).cpu().numpy().flatten()
    # rank sentences by similarity
    idxs = cos.argsort()[::-1][:max_sentences]
    summary = " ".join([sents[i] for i in sorted(idxs)])
    return summary

def llm_summary(text, model="openai"):
    """
    If OPENAI_API_KEY is set and you prefer LLM summaries, use that.
    Returns text summary or raises if not configured.
    """
    if os.getenv("OPENAI_API_KEY"):
        # simple OpenAI usage (openai package required)
        import openai
        openai.api_key = os.getenv("OPENAI_API_KEY")
        prompt = f"Summarize the following employee feedback in 3 concise bullet points:\n\n{text}\n\nBullets:"
        resp = openai.Completion.create(engine="text-davinci-003", prompt=prompt, max_tokens=200, temperature=0.0)
        return resp.choices[0].text.strip()
    else:
        raise RuntimeError("OPENAI_API_KEY not configured for llm_summary")
