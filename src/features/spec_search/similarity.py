from collections import Counter
from math import sqrt


def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def tokenize(text: str) -> Counter:
    return Counter(normalize_text(text).split())


def cosine_similarity(left_text: str, right_text: str) -> float:
    left = tokenize(left_text)
    right = tokenize(right_text)

    if not left or not right:
        return 0.0

    common_tokens = set(left) & set(right)
    numerator = sum(left[token] * right[token] for token in common_tokens)
    left_size = sqrt(sum(value * value for value in left.values()))
    right_size = sqrt(sum(value * value for value in right.values()))

    if not left_size or not right_size:
        return 0.0

    return numerator / (left_size * right_size)
