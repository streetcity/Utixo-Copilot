from flask import Flask, request, jsonify, send_from_directory
import mysql.connector, os, random
from mysql.connector import pooling
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.corpus import stopwords
import string

load_dotenv()
nltk.download("stopwords", quiet=True)
stop_words = set(stopwords.words("italian"))

def clean_text(text):
    text = text.lower()
    text = ''.join([c for c in text if c not in string.punctuation])
    words = [w for w in text.split() if w not in stop_words]
    return ' '.join(words)


app = Flask(__name__)

# ===== Connessione: usa un connection pool per efficienza =====
dbconfig = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "chatbot"),
}
pool = pooling.MySQLConnectionPool(pool_name="mypool", pool_size=5, **dbconfig)

def db_conn():
    return pool.get_connection()

# ===== Helpers DB =====
def get_all_faq():
    conn = db_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, categoria, domanda, risposta1, risposta2, risposta3 FROM faq")
        return cur.fetchall()
    finally:
        cur.close(); conn.close()

def insert_log(user_id, msg_utente, risposta):
    conn = db_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO logs (user_id, messaggio_utente, risposta_bot) VALUES (%s, %s, %s)",
            (user_id, msg_utente, risposta)
        )
        conn.commit()
    finally:
        cur.close(); conn.close()

# ===== Rotte web =====
@app.route('/')
def home():
    return "Backend chatbot attivo ✅"

@app.route('/chat')
def chat():
    return send_from_directory('static', 'index.html')

@app.route('/db-test')
def db_test():
    # verifica che il DB risponda e che ci siano FAQ
    faqs = get_all_faq()
    return jsonify({"ok": True, "faq_count": len(faqs)})

@app.route('/message', methods=['POST'])
def message():
    data = request.get_json() or {}
    user_msg = (data.get("message") or "").strip()
    if not user_msg:
        return jsonify({"reply": "Non ho ricevuto alcun messaggio.", "faq_matched_id": None})

    faqs = get_all_faq()
    if not faqs:
        return jsonify({"reply": "Database FAQ vuoto!", "faq_matched_id": None})

    # Prepara le domande e le pulisce
    domande = [clean_text(row["domanda"]) for row in faqs]
    user_clean = clean_text(user_msg)

    # TF-IDF: crea vettori numerici per ogni domanda + l'input utente
    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform(domande + [user_clean])

    # Calcola similarità coseno tra l'utente e ogni FAQ
    sim = cosine_similarity(vectors[-1], vectors[:-1])
    idx_best = sim.argmax()  # indice della FAQ più simile
    score_best = sim[0][idx_best]

    # Soglia minima di similarità (puoi regolarla)
    THRESHOLD = 0.25

    if score_best >= THRESHOLD:
        row = faqs[idx_best]
        candidati = [row["risposta1"], row["risposta2"], row["risposta3"]]
        candidati = [c for c in candidati if c]
        risposta = random.choice(candidati) if candidati else "Non ho una risposta precisa."
        best = row["id"]
    else:
        risposta = "Non ho trovato una risposta precisa, puoi riformulare?"
        best = None

    # Salva nel log
    insert_log(None, user_msg, risposta)

    return jsonify({
        "reply": risposta,
        "faq_matched_id": best,
        "similarity": round(float(score_best), 3)
    })

if __name__ == '__main__':
    # abilita accesso da LAN se serve
    app.run(host='0.0.0.0', port=5000, debug=True)
