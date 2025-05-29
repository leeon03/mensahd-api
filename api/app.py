from flask import Flask, Response, jsonify
import requests
import os

app = Flask(__name__)

@app.route('/api/mensa')
def get_combined_data():
    urls = [
        "https://cvzi.github.io/mensahd/meta/mannheim_metropol.xml",
        "https://cvzi.github.io/mensahd/meta/mannheim_greenes.xml"
    ]

    try:
        contents = []

        for url in urls:
            xml = requests.get(url).text
            if xml.startswith('<?xml'):
                xml = xml.split('\n', 1)[1]  # entferne erste Zeile
            contents.append(xml)

        combined = '<?xml version="1.0" encoding="UTF-8"?>\n' + "\n".join(contents)
        return Response(combined, mimetype="application/xml")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
