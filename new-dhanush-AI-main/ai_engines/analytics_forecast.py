"""
AI Analytics Engine:
- Hiring/attrition forecasting (Prophet)
- Employee clustering (KMeans/DBSCAN)
- AI insight summarization (LLaMA3 / GPT / extractive fallback)
"""
import pandas as pd, numpy as np, os
from prophet import Prophet
from sklearn.cluster import KMeans, DBSCAN
from sentence_transformers import SentenceTransformer, util

# ---------- FORECAST ----------
def forecast_hiring(df: pd.DataFrame, periods: int = 6):
    df = df.rename(columns={"date": "ds", "hired_count": "y"})
    model = Prophet(yearly_seasonality=True, weekly_seasonality=False)
    model.fit(df)
    future = model.make_future_dataframe(periods=periods, freq="M")
    forecast = model.predict(future)
    return forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(periods)

# ---------- CLUSTER ----------
def cluster_employees(df: pd.DataFrame, method="kmeans", k=4):
    X = df[["performance_score", "avg_hours", "sentiment", "salary"]].fillna(0)
    if method == "dbscan":
        model = DBSCAN(eps=0.5, min_samples=3)
        labels = model.fit_predict(X)
        centers = []
    else:
        model = KMeans(n_clusters=k, random_state=42)
        labels = model.fit_predict(X)
        centers = model.cluster_centers_.tolist()
    df["cluster"] = labels
    return df, centers

# ---------- INSIGHT SUMMARIZATION ----------
def summarize_insights(text: str):
    try:
        import openai, os
        openai.api_key = os.getenv("OPENAI_API_KEY")
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user",
                       "content": f"Summarize the following HR analytics insights in 3 concise bullet points:\n{text}"}],
            temperature=0
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        # fallback extractive summary
        sents = [s.strip() for s in text.split(".") if len(s.strip()) > 10]
        model = SentenceTransformer("all-MiniLM-L6-v2")
        embs = model.encode(sents, convert_to_tensor=True)
        centroid = embs.mean(dim=0)
        sim = util.cos_sim(embs, centroid).cpu().numpy().flatten()
        top = sim.argsort()[-3:][::-1]
        return ". ".join([sents[i] for i in top])
