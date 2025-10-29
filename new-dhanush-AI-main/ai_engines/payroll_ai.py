"""
AI helpers for payroll automation and anomaly detection.
"""
import numpy as np, pandas as pd
from sklearn.ensemble import IsolationForest
from xgboost import XGBRegressor
import os, joblib, datetime

ANOM_MODEL = "models_saved/attendance_iforest.joblib"
SAL_MODEL = "models_saved/salary_predictor.joblib"

# ---- Anomaly detection ----
def train_anomaly_model(df: pd.DataFrame):
    """
    df must contain columns: ['hours_worked','leaves','late_count']
    """
    clf = IsolationForest(contamination=0.05, random_state=42)
    clf.fit(df[["hours_worked","leaves","late_count"]])
    os.makedirs(os.path.dirname(ANOM_MODEL), exist_ok=True)
    joblib.dump(clf, ANOM_MODEL)
    return clf

def detect_anomalies(df: pd.DataFrame):
    """
    Returns df with 'anomaly'=True/False
    """
    if not os.path.exists(ANOM_MODEL):
        return df.assign(anomaly=False)
    clf = joblib.load(ANOM_MODEL)
    preds = clf.predict(df[["hours_worked","leaves","late_count"]])
    df["anomaly"] = preds == -1
    return df

# ---- Payroll / Salary prediction ----
def calculate_payroll(base_salary, total_hours, std_hours=160, overtime_rate=1.25, leave_penalty=0.02, leaves=0):
    overtime = max(0, total_hours - std_hours)
    overtime_bonus = overtime * (base_salary/std_hours) * (overtime_rate-1)
    leave_deduction = leaves * leave_penalty * (base_salary/22)
    return round(base_salary + overtime_bonus - leave_deduction, 2)

def train_salary_predictor(csv_path):
    df = pd.read_csv(csv_path)
    X = df[["total_hours","leaves","overtime_hours"]]
    y = df["final_salary"]
    model = XGBRegressor(n_estimators=150, max_depth=5, learning_rate=0.1)
    model.fit(X, y)
    os.makedirs(os.path.dirname(SAL_MODEL), exist_ok=True)
    joblib.dump(model, SAL_MODEL)
    return model

def predict_salary(features: dict):
    if not os.path.exists(SAL_MODEL):
        return calculate_payroll(features.get("base_salary",0),
                                 features.get("total_hours",0),
                                 leaves=features.get("leaves",0))
    model = joblib.load(SAL_MODEL)
    X = np.array([[features.get("total_hours",0),
                   features.get("leaves",0),
                   features.get("overtime_hours",0)]])
    return float(model.predict(X)[0])
