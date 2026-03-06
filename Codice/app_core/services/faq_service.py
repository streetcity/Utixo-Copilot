from __future__ import annotations

import hashlib
import os
from typing import Any, Dict, List, Optional

import numpy as np
from flask import current_app
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..db import get_connection
from ..utils.text_utils import clean_text

_FAQ_CACHE: Dict[str, Any] = {"fingerprint": None}



def get_all_faqs() -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, domanda, risposta1, risposta2, risposta3 FROM faq")
    rows = cur.fetchall() or []
    cur.close()
    conn.close()
    return rows



def _fingerprint_faqs(faqs: List[Dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for row in faqs:
        digest.update(str(row.get("id")).encode())
        digest.update((row.get("domanda") or "").encode("utf-8", errors="ignore"))
        digest.update((row.get("risposta1") or "").encode("utf-8", errors="ignore"))
        digest.update((row.get("risposta2") or "").encode("utf-8", errors="ignore"))
        digest.update((row.get("risposta3") or "").encode("utf-8", errors="ignore"))
    return digest.hexdigest()



def _build_faq_index(faqs: List[Dict[str, Any]]):
    questions_clean = [clean_text(row.get("domanda") or "") for row in faqs]

    vec_word = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    x_word = vec_word.fit_transform(questions_clean)

    vec_char = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1)
    x_char = vec_char.fit_transform(questions_clean)

    return questions_clean, vec_word, x_word, vec_char, x_char



def get_faq_index(faqs: List[Dict[str, Any]]):
    fingerprint = _fingerprint_faqs(faqs)
    if _FAQ_CACHE.get("fingerprint") != fingerprint:
        questions_clean, vec_word, x_word, vec_char, x_char = _build_faq_index(faqs)
        _FAQ_CACHE.update(
            {
                "fingerprint": fingerprint,
                "faqs": faqs,
                "questions_clean": questions_clean,
                "vec_word": vec_word,
                "x_word": x_word,
                "vec_char": vec_char,
                "x_char": x_char,
            }
        )
    return _FAQ_CACHE



def score_faqs(user_clean: str, cache: Dict[str, Any]):
    q_word = cache["vec_word"].transform([user_clean])
    q_char = cache["vec_char"].transform([user_clean])

    sim_word = cosine_similarity(q_word, cache["x_word"])[0]
    sim_char = cosine_similarity(q_char, cache["x_char"])[0]

    alpha = current_app.config["SIM_ALPHA_WORD"]
    sim = alpha * sim_word + (1.0 - alpha) * sim_char
    return sim, sim_word, sim_char



def match_faq(user_message: str) -> Dict[str, Any]:
    faqs = get_all_faqs()
    if not faqs:
        return {
            "reply": "Al momento non ho contenuti disponibili.",
            "matched_id": None,
            "similarity": 0.0,
            "suggestions": [],
            "need_clarification": False,
        }

    user_clean = clean_text(user_message)
    if not user_clean:
        return {
            "reply": "Puoi riformulare con più dettagli?",
            "matched_id": None,
            "similarity": 0.0,
            "suggestions": [],
            "need_clarification": True,
        }

    cache = get_faq_index(faqs)
    sim, _, _ = score_faqs(user_clean, cache)
    best_index = int(np.argmax(sim))
    best_score = float(sim[best_index])

    top_idx = sim.argsort()[::-1][: max(1, current_app.config["SUGGEST_TOPK"])]
    suggestions = []
    for idx in top_idx:
        row = faqs[int(idx)]
        suggestions.append(
            {
                "id": int(row["id"]),
                "domanda": (row.get("domanda") or "").strip(),
                "score": float(sim[int(idx)]),
            }
        )

    if best_score >= current_app.config["SIM_THRESHOLD"]:
        best_row = faqs[best_index]
        answers = [
            reply for reply in (
                best_row.get("risposta1"),
                best_row.get("risposta2"),
                best_row.get("risposta3"),
            ) if reply
        ]
        return {
            "reply": answers[0] if answers else "Non ho una risposta precisa.",
            "matched_id": int(best_row["id"]),
            "similarity": best_score,
            "suggestions": suggestions,
            "need_clarification": False,
        }

    if suggestions and float(suggestions[0]["score"]) >= current_app.config["SIM_LOW_HINT"]:
        reply = (
            "Non sono sicuro al 100% di cosa intendi. "
            "Puoi dirmi quale di questi casi è più vicino?\n\n"
            + "\n".join([f"{idx + 1}) {item['domanda']}" for idx, item in enumerate(suggestions)])
            + "\n\nRispondi con il numero (1/2/3) oppure aggiungi un dettaglio in più."
        )
    else:
        reply = (
            "Non ho trovato una risposta precisa. "
            "Puoi aggiungere un dettaglio in più, ad esempio prodotto, errore o schermata?"
        )

    return {
        "reply": reply,
        "matched_id": None,
        "similarity": best_score,
        "suggestions": suggestions,
        "need_clarification": True,
    }
