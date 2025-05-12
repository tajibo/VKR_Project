from sklearn.feature_extraction.text import TfidfVectorizer

vectorizer = TfidfVectorizer()


def vectorize(corpus: list[str]):
    """
    Обучает TF-IDF на корпусе и преобразует текст в вектор признаков.
    """
    return vectorizer.fit_transform(corpus)
