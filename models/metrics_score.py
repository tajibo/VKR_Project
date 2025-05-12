from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import joblib
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from collections import Counter


def paraphrase(text: str) -> str:
    """
    Генерация простых парафразов вопросов при обучении.
    """
    reps = [
        ("Какие", "Что нужно"),
        ("Что такое", "Опишите"),
        ("Как", "Каким образом"),
        ("Где", "В каком месте"),
    ]
    for a, b in reps:
        if text.startswith(a):
            return text.replace(a, b, 1)
    return text


def visualize_metrics(y_true, y_pred):
    """
    Визуализация метрик: Accuracy и F1.
    """
    accuracy = accuracy_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred, average='macro')

    # Плоты для метрик
    metrics = {'Accuracy': accuracy, 'F1 Score (Macro)': f1}

    # Построение графика
    plt.figure(figsize=(8, 6))
    plt.bar(metrics.keys(), metrics.values(), color=['skyblue', 'lightcoral'])
    plt.title('Model Evaluation Metrics')
    plt.ylabel('Score')
    plt.tight_layout()

    # Создание папки, если её нет
    metrics_dir = Path("models/metrics")
    metrics_dir.mkdir(parents=True, exist_ok=True)

    # Сохранение графика
    plt.savefig(metrics_dir / "metrics_plot.png")
    plt.close()
    print(f"Metrics plot saved to {metrics_dir / 'metrics_plot.png'}")


def main():
    # 1) Путь к CSV-файлу с исходными данными
    csv_path = Path("data/raw") / "vitte_faq.csv"

    # 2) Загрузка данных в DataFrame
    df = pd.read_csv(csv_path, sep=",", engine="python", quotechar='"', encoding="utf-8")

    # 3) Очистка и фильтрация категорий
    df["category"] = df["category"].astype(str).str.strip()
    df = df[~df["category"].isin(["", "nan", "None"])]
    if df.empty:
        raise RuntimeError(f"Нет размеченных примеров в {csv_path}")

    # 4) Формируем тексты и метки, добавляем парафразы
    texts, labels = [], []
    first_example = {}
    for _, row in df.iterrows():
        q, cat = row["question"], row["category"]
        texts.append(q)
        labels.append(cat)
        if cat not in first_example:
            first_example[cat] = q
        p = paraphrase(q)
        if p != q:
            texts.append(p)
            labels.append(cat)

    # 5) Дублируем категории с одним примером для корректной стратификации
    counts = Counter(labels)
    n_classes = len(counts)
    for cat, cnt in counts.items():
        while cnt < 2:
            texts.append(first_example[cat])
            labels.append(cat)
            cnt += 1

    # 6) Разбиение на train/test: по одному примеру каждого класса в тесте
    n_test = n_classes
    print(f"Используем test_size={n_test} (число классов) для stratify")
    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=n_test, random_state=42, stratify=labels
    )

    # 7) Векторизация TF-IDF (уни- и биграммы)
    vectorizer = TfidfVectorizer(
        max_features=5000, ngram_range=(1, 2), token_pattern=r"(?u)\b\w+\b"
    )
    X_tr = vectorizer.fit_transform(X_train)
    X_te = vectorizer.transform(X_test)

    # 8) Обучение модели логистической регрессии
    model = LogisticRegression(solver="lbfgs", max_iter=1000, class_weight="balanced")
    model.fit(X_tr, y_train)

    # 9) Оценка качества модели на тестовой выборке
    y_pred = model.predict(X_te)
    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average="macro")
    print(f"Accuracy: {accuracy:.3f}")
    print(f"F1 (macro): {f1:.3f}")

    # 10) Визуализация метрик
    visualize_metrics(y_test, y_pred)

    # 11) Сохранение обученных артефактов: векторизатора и модели
    art_dir = Path("models/artifacts")
    art_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(vectorizer, art_dir / "intent_vectorizer.pkl")
    joblib.dump(model, art_dir / "intent_model.pkl")
    print(f"Artifacts saved to {art_dir}")


if __name__ == "__main__":
    main()
