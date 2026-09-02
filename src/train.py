import joblib
import pandas as pd

from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import (accuracy_score, classification_report)
from xgboost import XGBClassifier
from preprocessing import (prepare_dataset, preprocessing_pipeline)

BASE_DIR = Path(__file__).resolve().parent
csv_path = BASE_DIR.parent / "data" / "fertilizer_recommendation.csv"

df = pd.read_csv(csv_path)

X, y, encoder = prepare_dataset(df)

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

pipeline = Pipeline([
    (
        "preprocessing",
        preprocessing_pipeline()
    ),
    (
        "classifier",
        XGBClassifier(
            random_state=42,
            objective="multi:softprob",
            eval_metric="mlogloss"
        )
    )
])

pipeline.fit( X_train, y_train )

y_pred = pipeline.predict(X_test)
accuracy = accuracy_score(
    y_test,
    y_pred
)

print(y_pred)
print("="*50)
print("Accuracy :", accuracy)
print("="*50)

print(
    classification_report(
        y_test,
        y_pred
    )
)

# BASE_DIR = Path(__file__).resolve().parent.parent
# MODEL_PATH = BASE_DIR / "models" / "fertilizer_pipeline.pkl"
# LABEL_ENCODER = BASE_DIR / "models" / "label_encoder.pkl"

# joblib.dump(pipeline, MODEL_PATH)
# joblib.dump(encoder, LABEL_ENCODER)