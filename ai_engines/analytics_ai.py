"""
AI Analytics Engine:
- Hiring/attrition forecasting via Prophet
- Employee clustering via KMeans/DBSCAN
- Insight summarization via LLaMA 3 or OpenAI API
"""
import pandas as pd, numpy as np, os, json
from prophet import Prophet
from sklearn.cluster import KMeans
from sentence_transformers import SentenceTransformer, util

# -------- Forecasting --------
def forecast_hiring_trends(csv_path, periods=6):
    df = pd.read_csv(csv_path)  # columns: date, hired_count
    df.rename(columns={"date":"ds","hired_count":"y"}, inplace=True)
    model = Prophet(yearly_seasonality=True, weekly_seasonality=False)
    model.fit(df)
    future = model.make_future_dataframe(periods=periods, freq="M")
    forecast = model.predict(future)
    return forecast[["ds","yhat","yhat_lower","yhat_upper"]].tail(periods)

# -------- Clustering --------
def cluster_employees(df: pd.DataFrame, k=4):
    """
    df columns: ['employee_id','performance_score','avg_hours','sentiment','salary']
    """
    X = df[["performance_score","avg_hours","sentiment","salary"]].fillna(0)
    model = KMeans(n_clusters=k, random_state=42)
    labels = model.fit_predict(X)
    df["cluster"] = labels
    centroids = model.cluster_centers_.tolist()
    return df, centroids

# -------- Insight Summarization --------
def summarize_insights(text):
    """Use LLaMA 3 / OpenAI GPT if available, else extractive."""
    try:
        import openai
        openai.api_key = os.getenv("OPENAI_API_KEY")
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role":"user",
                       "content":f"Summarize the following HR analytics in 3 concise insights:\n{text}"}],
            temperature=0)
        return resp.choices[0].message.content.strip()
    except Exception:
        # fallback extractive summarizer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        sents = [s.strip() for s in text.split(".") if len(s.strip())>10]
        embs = model.encode(sents, convert_to_tensor=True)
        centroid = embs.mean(dim=0)
        cos = util.cos_sim(embs, centroid).cpu().numpy().flatten()
        top = cos.argsort()[-3:][::-1]
        return ". ".join([sents[i] for i in top])
