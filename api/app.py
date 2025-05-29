from flask import Flask, Response, jsonify
import requests

app = Flask(__name__)

@app.route('/api/mensa')
def get_combined_data():
    urls = [
        "https://cvzi.github.io/mensahd/meta/mannheim_metropol.xml",
        "https://cvzi.github.io/mensahd/meta/mannheim_greenes.xml"
    ]

    try:
        contents = [requests.get(url).text for url in urls]
        combined = "\n".join(contents)
        return Response(combined, mimetype="application/xml")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
