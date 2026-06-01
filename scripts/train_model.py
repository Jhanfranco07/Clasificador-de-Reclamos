from pathlib import Path
import pandas as pd
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = BASE_DIR / "data" / "reclamos_entrenamiento.csv"
MODEL_PATH = BASE_DIR / "models" / "claim_classifier.joblib"
REPORT_PATH = BASE_DIR / "models" / "training_report.txt"

def train_model():
    df = pd.read_csv(DATASET_PATH)

    X = df["texto"].astype(str)
    y = df["categoria"].astype(str)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.25,
        random_state=42,
        stratify=y
    )

    model = Pipeline([
        ("tfidf", TfidfVectorizer(
            lowercase=True,
            strip_accents="unicode",
            ngram_range=(1, 2),
            min_df=1
        )),
        ("clf", LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            solver="lbfgs"
        ))
    ])

    model.fit(X_train, y_train)
    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    report = []
    report.append("SmartClaim AI - Reporte de entrenamiento del clasificador ML")
    report.append("=" * 70)
    report.append(f"Registros del dataset: {len(df)}")
    report.append(f"Categorias: {', '.join(sorted(df['categoria'].unique()))}")
    report.append(f"Accuracy de validacion: {accuracy:.4f}")
    report.append("")
    report.append(classification_report(y_test, predictions, zero_division=0))

    REPORT_PATH.write_text("\n".join(report), encoding="utf-8")

    print(f"Modelo entrenado y guardado en: {MODEL_PATH}")
    print(f"Reporte guardado en: {REPORT_PATH}")
    print(f"Accuracy: {accuracy:.4f}")

if __name__ == "__main__":
    train_model()
