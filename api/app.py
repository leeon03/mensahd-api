from flask import Flask, jsonify
import subprocess
import os

app = Flask(__name__)

@app.route('/api/mensa')
def get_mensa_data():
    # Starte den Parser für Mannheim
    subprocess.run(["python", "updateFeeds.py", "mannheim"])

    # Lade die erzeugte XML-Datei
    xml_path = os.path.join("out", "mannheim", "dhbw-mensa.xml")
    if not os.path.exists(xml_path):
        return jsonify({"error": "Speiseplan nicht gefunden"}), 404

    with open(xml_path, encoding="utf-8") as f:
        xml_data = f.read()

    return xml_data, 200, {'Content-Type': 'application/xml'}

if __name__ == "__main__":
    app.run(debug=True, port=5000)
