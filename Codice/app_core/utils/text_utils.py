from __future__ import annotations

import json
import random
import re
import urllib.request
from typing import Optional

from flask import current_app

FAQ_SYNONYMS = {
    "m365": "microsoft 365",
    "office365": "microsoft 365",
    "o365": "microsoft 365",
    "exo": "exchange online",
    "exchangeonline": "exchange online",
    "onedrive": "one drive",
    "sharepointonline": "sharepoint online",
    "teams": "microsoft teams",
    "pwd": "password",
    "pass": "password",
    "2fa": "autenticazione a due fattori",
    "mfa": "autenticazione a due fattori",
}


def _apply_synonyms(text: str) -> str:
    value = text
    for key, replacement in FAQ_SYNONYMS.items():
        value = re.sub(rf"\b{re.escape(key)}\b", replacement, value)
    return value


def clean_text(text: str) -> str:
    value = (text or "").lower()
    value = _apply_synonyms(value)
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _strip_llm_noise(text: str) -> str:
    value = (text or "").strip()
    if not value:
        return ""

    patterns_to_remove = [
        r"^certo[,!\.\s]*",
        r"^certamente[,!\.\s]*",
        r"^assolutamente[,!\.\s]*",
        r"^ti aiuto subito[:\s]*",
        r"^ecco la risposta[:\s]*",
        r"^ecco come funziona[:\s]*",
        r"^in base alla tua richiesta[,:\s]*",
        r"^gentile cliente[,:\s]*",
    ]

    for pattern in patterns_to_remove:
        value = re.sub(pattern, "", value, flags=re.IGNORECASE)

    value = re.sub(r"\n{3,}", "\n\n", value)
    value = re.sub(r"[ \t]+\n", "\n", value)
    value = re.sub(r"\n[ \t]+", "\n", value)
    value = re.sub(r"[ \t]{2,}", " ", value)
    return value.strip()


def _is_list_like(text: str) -> bool:
    value = (text or "").lstrip()
    return any(
        value.startswith(prefix)
        for prefix in ("- ", "• ", "1) ", "1. ", "2) ", "2. ", "* ")
    )


def _ollama_generate(prompt: str) -> Optional[str]:
    if not current_app.config["OLLAMA_ENABLED"]:
        return None

    model = (current_app.config.get("OLLAMA_MODEL") or "").strip()
    if not model:
        return None

    try:
        url = current_app.config["OLLAMA_HOST"].rstrip("/") + "/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": current_app.config.get("OLLAMA_KEEP_ALIVE", "5m"),
            "options": {
                "temperature": float(current_app.config.get("OLLAMA_TEMPERATURE", 0.15)),
                "num_predict": int(current_app.config.get("OLLAMA_MAX_TOKENS", 220)),
                "top_p": 0.9,
                "repeat_penalty": 1.08,
            },
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(req, timeout=float(current_app.config["OLLAMA_TIMEOUT"])) as resp:
            raw = resp.read().decode("utf-8", errors="replace")

        data = json.loads(raw) if raw else {}
        result = (data.get("response") or "").strip()
        result = _strip_llm_noise(result)
        return result or None
    except Exception:
        return None


def humanize_answer_fallback(answer: str) -> str:
    value = (answer or "").strip()
    if not value:
        return value

    short = len(value) < 160
    prefixes = [
        "Ti spiego meglio.",
        "Ecco la risposta in modo più chiaro.",
        "Ti confermo quanto segue.",
        "Questa è la procedura corretta.",
    ]
    suffixes = [
        "Se il tuo caso è leggermente diverso, scrivimi più dettagli.",
        "Se compare un errore specifico, incollamelo e ti aiuto a interpretarlo.",
        "Se vuoi, puoi indicarmi anche il servizio coinvolto.",
        "",
    ]

    if _is_list_like(value):
        formatted = value
    else:
        parts = [p.strip() for p in re.split(r"\n+|\.\s+", value) if p.strip()]
        if len(parts) >= 4:
            formatted = "\n".join([f"- {p}" for p in parts])
        else:
            formatted = value

    if short:
        return formatted

    return f"{random.choice(prefixes)}\n\n{formatted}\n\n{random.choice(suffixes)}".strip()


def _build_humanize_prompt(user_question: str, skeleton_answer: str) -> str:
    question = (user_question or "").strip()
    answer = (skeleton_answer or "").strip()

    return f"""
Sei Utixo Copilot, assistente clienti di Utixo.

Il tuo compito è RISCRIVERE una risposta base in modo più naturale, professionale, chiaro e piacevole da leggere.
Devi mantenere ESATTAMENTE lo stesso significato della risposta base.

DOMANDA DEL CLIENTE:
{question}

RISPOSTA BASE:
{answer}

REGOLE OBBLIGATORIE:
- non inventare nulla
- non aggiungere passaggi tecnici non presenti nella risposta base
- non aggiungere link, riferimenti, policy o promesse non presenti
- non parlare di "FAQ", "database", "prompt", "modello", "AI", "sistemi interni" o "team interni"
- non dire che stai riscrivendo o riformulando
- usa un tono professionale ma umano
- scrivi in italiano
- sii chiaro e diretto
- evita introduzioni inutili
- se la risposta base è già sintetica, mantienila sintetica
- se ci sono punti o step, mantieni una struttura ordinata
- non usare formule come "Certo!", "Assolutamente!", "Ecco la risposta:"
- restituisci SOLO il testo finale da mostrare al cliente

TESTO FINALE:
""".strip()


def humanize_answer(user_question: str, skeleton_answer: str) -> str:
    if not current_app.config["HUMANIZE_ENABLED"]:
        return skeleton_answer

    base_answer = (skeleton_answer or "").strip()
    if not base_answer:
        return base_answer

    min_chars = int(current_app.config.get("HUMANIZE_MIN_CHARS", 30))
    if len(base_answer) < min_chars:
        return base_answer

    prompt = _build_humanize_prompt(user_question, base_answer)
    output = _ollama_generate(prompt)

    if not output:
        return humanize_answer_fallback(base_answer)

    cleaned = _strip_llm_noise(output)
    if not cleaned:
        return humanize_answer_fallback(base_answer)

    return cleaned