# ai_engines/ats_predictor.py
"""
ATS predictor:

- If you have labeled training data in CSV (features + label), you can call train_model()
  which will train an XGBoost (or LightGBM) classifier/regressor and persist model to disk.
- If no model exists, the function `score_application()` will compute a reasonable combined score:
    final_score = weighted combination of resume_score (0..1) & interview_score (0..100) & experience
  and normalize to 0..100.

Usage:
    from ai_engines.ats_predictor import score_application, train_model, load_model
"""

import os
import json
import numpy as np

# try to import xgboost/lightgbm; fall back to sklearn
MODEL_PATH = "models_saved/ats_model.json"

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except Exception:
    XGBOOST_AVAILABLE = False

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except Exception:
    LIGHTGBM_AVAILABLE = False

from sklearn.ensemble import RandomForestRegressor
import joblib

# default model object (sklearn regressor) - lazy load
_model = None

def _ensure_model_dir():
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

def load_model():
    global _model
    if _model is not None:
        return _model
    if os.path.exists(MODEL_PATH):
        try:
            _model = joblib.load(MODEL_PATH)
            return _model
        except Exception:
            _model = None
    return None

def save_model(model):
    _ensure_model_dir()
    joblib.dump(model, MODEL_PATH)

def train_model(training_csv_path):
    """
    Train a simple regression model to predict final_score (0..100).
    CSV should have columns: resume_score (0..1), interview_score (0..100), experience_years, label_final_score (0..100).
    """
    import pandas as pd
    df = pd.read_csv(training_csv_path)
    features = df[["resume_score", "interview_score", "experience_years"]].fillna(0)
    labels = df["label_final_score"].fillna(0)
    # choose model
    if XGBOOST_AVAILABLE:
        model = xgb.XGBRegressor(n_estimators=100, max_depth=4, learning_rate=0.1)
        model.fit(features, labels)
    elif LIGHTGBM_AVAILABLE:
        model = lgb.LGBMRegressor(n_estimators=100, max_depth=6)
        model.fit(features, labels)
    else:
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(features, labels)
    save_model(model)
    return model

def predict_with_model(resume_score, interview_score, experience_years):
    model = load_model()
    if not model:
        return None
    X = np.array([[resume_score, interview_score, experience_years]], dtype=float)
    try:
        pred = model.predict(X)[0]
        return float(pred)
    except Exception:
        return None

def score_application(resume_score, interview_score, experience_years):
    """
    Fallback scoring if no model:
    - resume_score: 0..1
    - interview_score: 0..100
    - experience_years: float

    We compute a weighted score:
       base = resume_score * 50  (max 50)
       interview_component = (interview_score / 100) * 40 (max 40)
       experience_component = min(10, experience_years / 5 * 10) (max 10)
    final = clamp(base + interview_component + experience_component, 0..100)
    """

    rs = float(resume_score or 0.0)
    iscore = float(interview_score or 0.0)
    exp = float(experience_years or 0.0)

    # try model first if available
    model_pred = predict_with_model(rs, iscore, exp)
    if model_pred is not None:
        # ensure 0..100
        return round(max(0.0, min(100.0, float(model_pred))), 2)

    base = rs * 50.0
    interview_comp = (iscore / 100.0) * 40.0
    experience_comp = min(10.0, (exp / 5.0) * 10.0)
    final = base + interview_comp + experience_comp
    final = max(0.0, min(100.0, final))
    return round(final, 2)
