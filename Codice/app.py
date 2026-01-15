from flask import Flask, request, jsonify, send_from_directory
import os
import random
from dotenv import load_dotenv
import mysql.connector

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 1-Carico le variabili dal file .env
load_dotenv()

# 2-Creo app Flask
app = Flask(__name__)

# 3-Leggo i dati del database
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "chatbot")
DB_PORT = int(os.getenv("DB_PORT", "3306"))

# 4-Stopwords
STOPWORDS = [
    "a","ad","al","alla","alle","allo","ai","agli","anche","che","chi","ci","con","come",
    "da","dal","dalla","delle","del","di","e","ed","è","gli","ha","hai","ho","i","il","in",
    "io","la","le","lo","loro","ma","mi","ne","nel","nella","no","non","o","per","poi",
    "se","sei","si","su","tra","un","una","uno","voi"
]

# 5-Funzione per pulire una frase
def clean_text(text):
    text = (text or "").lower()

    # rimuovo punteggiatura
    for ch in [".", ",", "!", "?", ":", ";", "(", ")", "[", "]", "{", "}", "'", '"', "-", "_", "/"]:
        text = text.replace(ch, " ")

    words = text.split()

    # tolgo le stopwords
    new_words = []
    for w in words:
        if w not in STOPWORDS:
            new_words.append(w)

    return " ".join(new_words)

# 6-Funzione che crea una connessione MySQL
def get_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT
    )

# 7-Rotte
@app.get("/")
def home():
    return "Backend chatbot attivo"

@app.get("/chat")
def chat():
    return send_from_directory("static", "index.html")

@app.get("/db-test")
def db_test():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM faq")
    count = cur.fetchone()[0]

    cur.close()
    conn.close()

    return jsonify({"ok": True, "faq_count": count})

@app.post("/message")
def message():
    data = request.get_json() or {}
    user_msg = (data.get("message") or "").strip()

    if user_msg == "":
        return jsonify({"reply": "Non ho ricevuto alcun messaggio.", "faq_matched_id": None})

    # prendo tutte le FAQ dal DB
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT id, domanda, risposta1, risposta2, risposta3 FROM faq")
    faqs = cur.fetchall()

    cur.close()
    conn.close()

    if len(faqs) == 0:
        return jsonify({"reply": "Database FAQ vuoto!", "faq_matched_id": None})

    # preparo le domande pulite
    domande_pulite = []
    for row in faqs:
        domande_pulite.append(clean_text(row["domanda"]))

    user_clean = clean_text(user_msg)

    if user_clean == "":
        return jsonify({"reply": "Puoi riformulare con più dettagli?", "faq_matched_id": None})

    # faccio TF-IDF e similarità
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(domande_pulite + [user_clean])

    sim = cosine_similarity(X[-1], X[:-1])[0]

    # prendo la migliore
    best_index = int(sim.argmax())
    best_score = float(sim[best_index])

    # soglia di similarità
    THRESHOLD = float(os.getenv("SIM_THRESHOLD", "0.25"))

    if best_score >= THRESHOLD:
        best_row = faqs[best_index]

        risposte = []
        if best_row["risposta1"]:
            risposte.append(best_row["risposta1"])
        if best_row["risposta2"]:
            risposte.append(best_row["risposta2"])
        if best_row["risposta3"]:
            risposte.append(best_row["risposta3"])

        if len(risposte) > 0:
            reply = random.choice(risposte)
        else:
            reply = "Non ho una risposta precisa."

        matched_id = best_row["id"]
    else:
        reply = "Non ho trovato una risposta precisa."
        matched_id = None

    # salvo un log
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO logs (user_id, messaggio_utente, risposta_bot) VALUES (%s, %s, %s)",
        (None, user_msg, reply)
    )
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "reply": reply,
        "faq_matched_id": matched_id,
        "similarity": round(best_score, 3)
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)