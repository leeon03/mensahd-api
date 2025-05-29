from flask import Flask, jsonify
import subprocess
import os

app = Flask(__name__)

@app.route('/api/mensa')
def get_mensa_data():
    # Nur die gewünschten Locations abrufen
    for location in ["metropol", "greenes"]:
        subprocess.run(["python", "updateFeeds.py", "mannheim", location])

    xml_path = os.path.join("mannheim", "dhbw-mensa.xml")
    if not os.path.exists(xml_path):
        return jsonify({"error": "Speiseplan nicht gefunden"}), 404

    with open(xml_path, encoding="utf-8") as f:
        xml_data = f.read()

    return xml_data, 200, {'Content-Type': 'application/xml'}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
