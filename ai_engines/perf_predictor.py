"""
Predictors for burnout / attrition risk.

- `train_attrition_model(training_csv)` trains a RandomForest/XGBoost regressor/classifier if labeled data exists.
- `predict_risk(features_dict)` returns a dictionary with keys: {'burnout_risk': 0..1, 'attrition_risk': 0..1}
- A fallback heuristic is provided if no model exists.
"""

import os, joblib, numpy as np

MODEL_PATH = "models_saved/perf_predictor.joblib"
_model = None

def load_model():
    global _model
    if _model:
        return _model
    if os.path.exists(MODEL_PATH):
        try:
            _model = joblib.load(MODEL_PATH)
            return _model
        except Exception:
            _model = None
    return None

def save_model(model):
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)

def train_attrition_model(csv_path):
    """
    CSV columns expected: avg_polarity, hours_worked_avg, leaves_per_month, tasks_completed_avg, label_attrition(0/1), label_burnout(0/1)
    Trains a multi-output regressor/classifier and saves model.
    """
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier
    df = pd.read_csv(csv_path)
    features = df[["avg_polarity","hours_worked_avg","leaves_per_month","tasks_completed_avg"]].fillna(0)
    # Try multi-output classifier using two separate classifiers
    clf_attr = RandomForestClassifier(n_estimators=200, random_state=42)
    clf_burnout = RandomForestClassifier(n_estimators=200, random_state=42)
    clf_attr.fit(features, df["label_attrition"].fillna(0).astype(int))
    clf_burnout.fit(features, df["label_burnout"].fillna(0).astype(int))
    save_model({"attrition": clf_attr, "burnout": clf_burnout})
    return True

def predict_risk(features: dict):
    """
    features expected keys: avg_polarity (-1..1), hours_worked_avg, leaves_per_month, tasks_completed_avg
    Returns floats 0..1
    """
    model = load_model()
    f = [
        float(features.get("avg_polarity", 0.0)),
        float(features.get("hours_worked_avg", 0.0)),
        float(features.get("leaves_per_month", 0.0)),
        float(features.get("tasks_completed_avg", 0.0))
    ]
    if model:
        try:
            X = np.array([f])
            a_prob = model["attrition"].predict_proba(X)[:,1][0] if hasattr(model["attrition"], "predict_proba") else model["attrition"].predict(X)[0]
            b_prob = model["burnout"].predict_proba(X)[:,1][0] if hasattr(model["burnout"], "predict_proba") else model["burnout"].predict(X)[0]
            return {"attrition_risk": float(a_prob), "burnout_risk": float(b_prob)}
        except Exception:
            pass
    # fallback heuristic:
    avg_polarity, hours, leaves, tasks = f
    # polarity negative -> increase risk
    polarity_risk = max(0.0, min(1.0, ( -avg_polarity + 1.0 ) / 2.0 ))  # if polarity -1 => risk 1
    hours_risk = max(0.0, min(1.0, (hours - 40.0) / 40.0))  # >40 hours increases risk
    leaves_risk = max(0.0, min(1.0, leaves / 4.0))
    tasks_risk = 1.0 - max(0.0, min(1.0, tasks / 10.0))    # fewer completed tasks -> higher burnout risk
    burnout = min(1.0, 0.5 * hours_risk + 0.3 * leaves_risk + 0.2 * tasks_risk)
    attrition = min(1.0, 0.5 * polarity_risk + 0.3 * leaves_risk + 0.2 * (1.0 - tasks / (tasks+1.0)))
    return {"attrition_risk": round(attrition, 3), "burnout_risk": round(burnout, 3)}
