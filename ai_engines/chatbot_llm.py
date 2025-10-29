# ai_engines/chatbot_llm.py
"""
Chatbot engine:
- Uses SentenceTransformers embeddings + ChromaDB for semantic retrieval
- Builds a prompt with retrieved context and calls LLM (OpenAI or local HF) to answer
- Provides document ingestion utilities
"""

import os
import json
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer, util
from typing import List, Dict, Any
from utils.doc_utils import extract_text_from_file
from pathlib import Path
import logging

# Setup Chroma client (local by default)
_CHROMA_DIR = os.getenv("CHROMA_DIR", "chroma_db")
_client = None
_collection = None
_EMBED_MODEL = None

def _get_embedding_model():
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        _EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _EMBED_MODEL

def _get_chroma_client():
    global _client, _collection
    if _client is None:
        # using local chroma persistence
        _client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory=_CHROMA_DIR))
    return _client

def get_collection(name="hr_docs"):
    client = _get_chroma_client()
    try:
        coll = client.get_collection(name)
    except Exception:
        coll = client.create_collection(name)
    return coll

# -------- ingestion ----------
def ingest_document(file_path: str, doc_id: str = None, metadata: Dict[str, Any] = None, collection_name="hr_docs", chunk_size=800, overlap=100):
    """
    Extracts text from file, chunks it, creates embeddings and stores in Chroma.
    - file_path: local path to file
    - doc_id: optional id, uses filename if None
    - metadata: optional dict stored with each chunk
    """
    text = extract_text_from_file(file_path)
    if not text:
        return {"ok": False, "error": "no_text_extracted"}
    # simple chunker by characters
    chunks = []
    start = 0
    L = len(text)
    while start < L:
        end = min(L, start + chunk_size)
        chunk = text[start:end]
        # try not to break mid-sentence (naive)
        if end < L:
            # extend to nearest space
            extra = text[end:end+50]
            m = re.search(r'\.|\n', extra)
            if m:
                end += m.start()
                chunk = text[start:end]
        chunks.append(chunk.strip())
        start = end - overlap

    # embed and upsert into chroma
    coll = get_collection(collection_name)
    model = _get_embedding_model()
    embeddings = model.encode(chunks, convert_to_numpy=True, show_progress_bar=False)

    # prepare ids and metadatas
    base_id = doc_id or Path(file_path).name
    ids = [f"{base_id}__{i}" for i in range(len(chunks))]
    metadatas = []
    for i, chunk in enumerate(chunks):
        md = metadata.copy() if metadata else {}
        md.update({"source": Path(file_path).name, "chunk_index": i})
        metadatas.append(md)
    coll.add(ids=ids, embeddings=embeddings.tolist(), metadatas=metadatas, documents=chunks)
    # persist
    _get_chroma_client().persist()
    return {"ok": True, "chunks_indexed": len(chunks), "source": Path(file_path).name}

# -------- retrieval ----------
def retrieve_context(query: str, collection_name="hr_docs", top_k=4):
    coll = get_collection(collection_name)
    embed_model = _get_embedding_model()
    q_emb = embed_model.encode(query, convert_to_numpy=True)
    results = coll.query(query_embeddings=q_emb.tolist(), n_results=top_k, include=["documents","metadatas","distances"])
    # results is a dict; normalize to list of texts
    docs = []
    for docs_list in results.get("documents", []):
        for d in docs_list:
            docs.append(d)
    # but chroma returns nested lists per query; we assume single query
    docs = results["documents"][0] if "documents" in results else []
    metadatas = results["metadatas"][0] if "metadatas" in results else []
    distances = results["distances"][0] if "distances" in results else []
    context_pieces = []
    for doc, md, dist in zip(docs, metadatas, distances):
        context_pieces.append({"text": doc, "meta": md, "distance": dist})
    return context_pieces

# -------- LLM call ----------
def _call_openai_chat(prompt: str, temperature: float = 0.0, max_tokens: int = 512):
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")
    resp = openai.ChatCompletion.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role":"system","content":"You are an HR assistant. Answer helpfully and concisely."},
                  {"role":"user","content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens
    )
    return resp.choices[0].message.content.strip()

def _call_local_llm(prompt: str, model_name: str = "meta-llama/Llama-2-7b-chat-hf", max_new_tokens: int = 256):
    """
    Local generation via Hugging Face transformers pipeline.
    This requires heavy setup and appropriate hardware. Keep as optional.
    """
    try:
        from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
        model = AutoModelForCausalLM.from_pretrained(model_name, device_map="auto", torch_dtype="auto")
        gen = pipeline("text-generation", model=model, tokenizer=tokenizer, max_new_tokens=max_new_tokens)
        out = gen(prompt, do_sample=False)[0]["generated_text"]
        return out
    except Exception as e:
        logging.exception("Local LLM call failed")
        return "Sorry — local LLM generation is not available on this server."

def generate_answer(query: str, context_pieces: List[Dict[str, Any]], use_openai: bool = True, extra_instructions: str = ""):
    """
    Build a prompt with context and call LLM.
    """
    # build context string
    ctx_parts = []
    for i, p in enumerate(context_pieces):
        src = p.get("meta", {}).get("source", "doc")
        ctx_parts.append(f"Context {i+1} (source: {src}):\n{p['text']}\n---")
    ctx_text = "\n\n".join(ctx_parts)

    prompt = f"""
You are an HR assistant. Use the provided context to answer the user's question. If the context does not contain the answer, say so and give concise guidance on where to find it.

CONTEXT:
{ctx_text}

USER QUESTION:
{query}

INSTRUCTIONS:
- Answer in concise bullet points.
- If the question is about a company policy, cite the source file (source: filename).
- If you don't know, say 'I couldn't find a direct answer in the provided documents.' and suggest who to contact.
{extra_instructions}
"""

    if use_openai and os.getenv("OPENAI_API_KEY"):
        return _call_openai_chat(prompt)
    else:
        return _call_local_llm(prompt)
