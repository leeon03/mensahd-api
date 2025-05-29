from flask import Flask, jsonify
import requests
import xmltodict
import os

app = Flask(__name__)

@app.route('/api/mensa')
def get_mensa_meals():
    urls = [
        "https://cvzi.github.io/mensahd/feed/mannheim_metropol.xml",
        "https://cvzi.github.io/mensahd/feed/mannheim_greenes.xml"
    ]

    all_meals = []

    for url in urls:
        xml = requests.get(url).text
        data = xmltodict.parse(xml)

        days = data.get('openmensa', {}).get('day', [])
        if isinstance(days, dict):  # Einzelner Tag
            days = [days]

        for day in days:
            date = day.get('@date')
            meals = day.get('meal', [])
            if isinstance(meals, dict):  # Einzelnes Gericht
                meals = [meals]

            for meal in meals:
                all_meals.append({
                    "date": date,
                    "name": meal.get('name'),
                    "category": meal.get('@category'),
                    "prices": meal.get('price')  # dict mit 'student', 'employee' etc.
                })

    return jsonify(all_meals)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
