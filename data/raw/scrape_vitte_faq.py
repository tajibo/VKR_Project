import csv
from pathlib import Path

import requests
from bs4 import BeautifulSoup


def scrape_faq(url: str):
    """Собирает пары (question, answer) с FAQ страницы Витте."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/90.0.4430.93 Safari/537.36"
        ),
        "Accept": "text/html",
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    items = soup.select("div.accordion-item.faq__item")
    print(f"[scrape] Found {len(items)} FAQ items on the page")

    faq_data = []
    for item in items:
        q_el = item.select_one(
            "button.accordion-button.faq__button, button.accordion-button"
        )
        question = q_el.get_text(strip=True) if q_el else None

        a_el = item.select_one("div.accordion-body.faq__body, div.accordion-body")
        answer = None
        if a_el:
            p_tags = a_el.select("p")
            if p_tags:
                answer = "\n".join(p.get_text(strip=True) for p in p_tags)
            else:
                answer = a_el.get_text(" ", strip=True)

        if question and answer:
            faq_data.append((question, answer))

    return faq_data


def save_to_csv(data, out_path: Path):
    """Сохраняет список (question, answer) в CSV с колонками question, answer, category."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["question", "answer", "category"])
        for q, a in data:
            writer.writerow([q, a, ""])  # категория задаётся вручную позже
    print(f"[scrape] Saved {len(data)} QA pairs to {out_path}")


if __name__ == "__main__":
    URL = "https://www.muiv.ru/studentu/faq/"
    faq = scrape_faq(URL)
    save_to_csv(faq, Path(__file__).parent / "vitte_faq.csv")
