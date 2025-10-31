from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
#def home():
#    return "Ciao, sono il chatbot!"

@app.route('/message', methods=['POST'])
def message():
    data = request.get_json()
    user_msg = data.get("message", "")
    return jsonify({"reply": f"Hai detto: {user_msg}"})

from flask import Flask, request, jsonify, send_from_directory

@app.route('/chat')
def chat():
    return send_from_directory('static', 'index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)