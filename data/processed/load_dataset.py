# data/processed/load_dataset.py
import csv
import os
from typing import List, Tuple


def load_dataset(path: str) -> Tuple[List[str], List[str]]:
    texts: List[str] = []
    labels: List[str] = []

    for filename in os.listdir(path):
        if not filename.endswith(".csv"):
            continue
        full = os.path.join(path, filename)
        with open(full, encoding="utf-8") as f:
            reader = csv.reader(f)
            _ = next(reader, None)  # пропускаем заголовок
            for row in reader:
                if len(row) < 3:
                    continue
                question = row[0].strip()
                category = row[2].strip()
                if question and category:
                    texts.append(question)
                    labels.append(category)
    return texts, labels
