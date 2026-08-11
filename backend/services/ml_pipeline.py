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
import mlflow
import mlflow.sklearn
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
MIN_REAL_SAMPLES = 30


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


def generate_synthetic_dataset(n_samples: int = 800, random_seed: int = 42) -> pd.DataFrame:
    """
    Generate synthetic server risk training data.
    Used as augmentation when real DB samples are insufficient.
    The risk formula mirrors the rule-based risk_engine.py weights.
    """
    np.random.seed(random_seed)
    cpu = np.random.uniform(5, 100, n_samples)
    memory = np.random.uniform(10, 100, n_samples)
    disk = np.random.uniform(10, 100, n_samples)
    uptime = np.random.uniform(1, 1000, n_samples)
    errors = np.random.poisson(lam=5, size=n_samples)

    # Risk formula matches the rule-based engine weights
    risk = (
        0.35 * cpu +
        0.30 * memory +
        0.25 * disk +
        0.02 * np.minimum(uptime, 365) +
        1.5 * np.minimum(errors, 50) +
        np.random.normal(0, 2.5, n_samples)
    )
    risk = np.clip(risk, 0, 100)

    return pd.DataFrame({
        "cpu": cpu, "memory": memory, "disk": disk,
        "uptime": uptime, "errors": errors, "risk_score": risk
    })


def build_training_dataset(db=None) -> pd.DataFrame:
    """
    Build a training dataset from real server DB records, augmented with synthetic data.
    Real data takes precedence; synthetic samples fill the gap if real count < MIN_REAL_SAMPLES.
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


def train_and_evaluate_pipeline(db=None) -> dict:
    """
    Executes end-to-end ML pipeline with MLflow tracking.
    Accepts an optional db session to train on real server data.
    """
    mlflow.set_experiment(EXPERIMENT_NAME)

    df = build_training_dataset(db=db)
    X = df[["cpu", "memory", "disk", "uptime", "errors"]]
    y = df["risk_score"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    n_estimators = 150
    max_depth = 12
    random_state = 42

    with mlflow.start_run() as run:
        run_id = run.info.run_id

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

        # Evaluation
        predictions = model.predict(X_test)
        mse = mean_squared_error(y_test, predictions)
        rmse = float(np.sqrt(mse))
        mae = float(mean_absolute_error(y_test, predictions))
        r2 = float(r2_score(y_test, predictions))

        # Real feature importance from model
        feature_names = list(X.columns)
        if hasattr(model, "feature_importances_"):
            raw_imp = model.feature_importances_
            importances = {name: round(float(v), 4) for name, v in zip(feature_names, raw_imp)}
        else:
            importances = {"cpu": 0.35, "memory": 0.30, "disk": 0.25, "errors": 0.08, "uptime": 0.02}

        # Drift detection: compare R² against baseline threshold
        prev_meta = _load_model_meta()
        prev_r2 = prev_meta.get("r2_score", 1.0)
        drift_detected = r2 < DRIFT_R2_THRESHOLD or (prev_r2 - r2) > 0.15
        if drift_detected:
            logger.warning(f"ML drift detected: new R²={r2:.3f}, previous R²={prev_r2:.3f}, threshold={DRIFT_R2_THRESHOLD}")

        # MLflow logging
        mlflow.log_param("model_type", model_name)
        mlflow.log_param("n_estimators", n_estimators)
        mlflow.log_param("max_depth", max_depth)
        mlflow.log_param("dataset_samples", len(df))
        mlflow.log_param("real_samples", len([r for r in df.itertuples() if True]))
        mlflow.log_metric("mse", float(mse))
        mlflow.log_metric("rmse", rmse)
        mlflow.log_metric("mae", mae)
        mlflow.log_metric("r2_score", r2)
        mlflow.log_metric("drift_detected", int(drift_detected))

        try:
            mlflow.sklearn.log_model(model, name="model")
        except Exception as e:
            logger.warning(f"MLflow model log notice: {e}")

        # Save trained pickle model for risk_engine.py
        with open(MODEL_PATH, "wb") as f:
            pickle.dump(model, f)

        # Save metadata for future drift comparisons
        meta = {
            "run_id": run_id,
            "model_type": model_name,
            "r2_score": r2,
            "rmse": rmse,
            "mae": mae,
            "drift_detected": drift_detected,
            "feature_importance": importances,
            "trained_at": datetime.utcnow().isoformat(),
            "dataset_samples": len(df),
        }
        _save_model_meta(meta)

        # Reload risk_engine cached model
        try:
            from services import risk_engine
            risk_engine._load_model()
        except Exception:
            pass

        return {
            "status": "success",
            "run_id": run_id,
            "experiment_name": EXPERIMENT_NAME,
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
        }


if __name__ == "__main__":
    result = train_and_evaluate_pipeline()
    print("MLflow Training Complete:", result)
