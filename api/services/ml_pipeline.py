"""
ML Pipeline & MLflow Experiment Tracking Engine
- Trains on REAL server data from the database (augmented with synthetic samples if insufficient)
- XGBoost / RandomForest regressor
- MLflow tracking: params, metrics, artifacts
- Real feature importance from trained model
- Drift detection: compares R² against baseline threshold
"""
import os
import pickle
import json
import logging
import numpy as np
import pandas as pd
try:
    import mlflow
    import mlflow.sklearn
    HAS_MLFLOW = True
except Exception:
    mlflow = None
    HAS_MLFLOW = False

from datetime import datetime
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "risk_model.pkl")
MODEL_META_PATH = os.path.join(os.path.dirname(__file__), "risk_model_meta.json")
EXPERIMENT_NAME = "Server_Risk_Scoring_Model"

# Minimum R² to consider model healthy (below = drift detected)
DRIFT_R2_THRESHOLD = 0.70
# Minimum real samples to train on real data; below this, supplement with synthetic
MIN_REAL_SAMPLES = 50


def _load_model_meta() -> dict:
    """Load saved model metadata (R², feature importance, last train date)."""
    if os.path.exists(MODEL_META_PATH):
        try:
            with open(MODEL_META_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_model_meta(meta: dict):
    """Persist model metadata alongside the pkl."""
    try:
        with open(MODEL_META_PATH, "w") as f:
            json.dump(meta, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not save model meta: {e}")


def generate_synthetic_dataset(n_samples: int = 1000) -> pd.DataFrame:
    """Generate realistic synthetic server telemetry data for bootstrapping."""
    np.random.seed(42)
    cpu = np.random.uniform(5, 99, n_samples)
    memory = np.random.uniform(10, 99, n_samples)
    disk = np.random.uniform(10, 99, n_samples)
    uptime = np.random.uniform(1, 1000, n_samples)
    errors = np.random.poisson(lam=5, size=n_samples)

    risk_score = (
        cpu * 0.35 +
        memory * 0.30 +
        disk * 0.25 +
        np.minimum(errors * 2, 20) +
        np.where(uptime > 365, 5, 0) +
        np.random.normal(0, 3, n_samples)
    )
    risk_score = np.clip(risk_score, 0, 100).round()

    return pd.DataFrame({
        "cpu": cpu,
        "memory": memory,
        "disk": disk,
        "uptime": uptime,
        "errors": errors,
        "risk_score": risk_score
    })


def build_training_dataset(db=None) -> pd.DataFrame:
    """
    Build training dataset combining real server metrics from DB
    and synthetic samples when real sample count is small.
    """
    real_rows = []

    if db is not None:
        try:
            from models import Server
            servers = db.query(Server).all()
            for s in servers:
                cpu = float(s.cpu_usage or 0)
                memory = float(s.memory_usage or 0)
                disk = float(s.disk_usage or 0)
                uptime = float(s.uptime_days or 0)
                errors = float(s.error_count or 0)
                risk = float(s.risk_score or 0)
                # Only include records with meaningful data
                if cpu > 0 or memory > 0 or disk > 0:
                    real_rows.append({
                        "cpu": cpu, "memory": memory, "disk": disk,
                        "uptime": uptime, "errors": errors, "risk_score": risk
                    })
        except Exception as e:
            logger.warning(f"Could not query server data for ML training: {e}")

    real_count = len(real_rows)
    logger.info(f"ML Training: {real_count} real server records collected from DB.")

    # Synthetic samples: if we have < MIN_REAL_SAMPLES real records, bulk with synthetic
    if real_count < MIN_REAL_SAMPLES:
        n_synthetic = max(800, MIN_REAL_SAMPLES * 10 - real_count)
        synthetic_df = generate_synthetic_dataset(n_samples=n_synthetic)
        logger.info(f"ML Training: augmenting with {n_synthetic} synthetic samples.")
        if real_rows:
            real_df = pd.DataFrame(real_rows)
            # Real data gets 3× weight via repetition
            df = pd.concat([real_df] * 3 + [synthetic_df], ignore_index=True)
        else:
            df = synthetic_df
    else:
        # Enough real data — no synthetic needed (minimal synthetic for regularisation)
        real_df = pd.DataFrame(real_rows)
        synthetic_df = generate_synthetic_dataset(n_samples=200)
        df = pd.concat([real_df, synthetic_df], ignore_index=True)

    return df.sample(frac=1, random_state=42).reset_index(drop=True)


def _train_core_model(df) -> dict:
    X = df[["cpu", "memory", "disk", "uptime", "errors"]]
    y = df["risk_score"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    n_estimators = 150
    max_depth = 12
    random_state = 42

    # Prefer XGBoost; fall back to RandomForest
    try:
        from xgboost import XGBRegressor
        model = XGBRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            learning_rate=0.08,
            subsample=0.85,
            colsample_bytree=0.85
        )
        model.fit(X_train, y_train)
        model_name = "XGBoost"
    except Exception as e:
        logger.info(f"XGBoost unavailable ({e}), using RandomForestRegressor.")
        model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            n_jobs=-1
        )
        model.fit(X_train, y_train)
        model_name = "RandomForest"

    predictions = model.predict(X_test)
    mse = mean_squared_error(y_test, predictions)
    rmse = float(np.sqrt(mse))
    mae = float(mean_absolute_error(y_test, predictions))
    r2 = float(r2_score(y_test, predictions))

    feature_names = list(X.columns)
    if hasattr(model, "feature_importances_"):
        raw_imp = model.feature_importances_
        importances = {name: round(float(v), 4) for name, v in zip(feature_names, raw_imp)}
    else:
        importances = {"cpu": 0.35, "memory": 0.30, "disk": 0.25, "errors": 0.08, "uptime": 0.02}

    prev_meta = _load_model_meta()
    prev_r2 = prev_meta.get("r2_score", 1.0)
    drift_detected = r2 < DRIFT_R2_THRESHOLD or (prev_r2 - r2) > 0.15

    # Save trained pickle model for risk_engine.py
    try:
        with open(MODEL_PATH, "wb") as f:
            pickle.dump(model, f)
    except Exception as save_err:
        logger.warning(f"Could not save model file: {save_err}")

    # Save metadata for future drift comparisons
    meta = {
        "status": "success",
        "model_type": model_name,
        "metrics": {
            "rmse": round(rmse, 4),
            "mae": round(mae, 4),
            "r2_score": round(r2, 4)
        },
        "feature_importance": importances,
        "model_path": MODEL_PATH,
        "drift_detected": drift_detected,
        "dataset_samples": len(df),
        "trained_at": datetime.utcnow().isoformat(),
    }
    _save_model_meta(meta)

    # Reload risk_engine cached model
    try:
        from services import risk_engine
        risk_engine._load_model()
    except Exception:
        pass

    return meta


def train_and_evaluate_pipeline(db=None) -> dict:
    """
    Executes end-to-end ML pipeline with optional MLflow tracking.
    """
    df = build_training_dataset(db=db)

    if HAS_MLFLOW and mlflow:
        try:
            mlflow.set_experiment(EXPERIMENT_NAME)
            with mlflow.start_run() as run:
                meta = _train_core_model(df)
                mlflow.log_params({"model_type": meta["model_type"], "n_samples": meta["dataset_samples"]})
                mlflow.log_metrics({"r2": meta["metrics"]["r2_score"], "rmse": meta["metrics"]["rmse"], "mae": meta["metrics"]["mae"]})
                meta["run_id"] = run.info.run_id
                meta["experiment_name"] = EXPERIMENT_NAME
                return meta
        except Exception as e:
            logger.warning(f"MLflow tracking skipped ({e}), executing standard pipeline.")

    return _train_core_model(df)


if __name__ == "__main__":
    result = train_and_evaluate_pipeline()
    print("MLflow Training Complete:", result)
