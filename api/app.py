from flask import Flask, jsonify
import requests
import xmltodict

app = Flask(__name__)

@app.route('/api/mensa')
def get_mensa_data():
    url = "https://cvzi.github.io/mensahd/feed/mannheim_metropol.xml"
    xml = requests.get(url).text
    data = xmltodict.parse(xml)

    days = data.get('openmensa', {}).get('canteen', {}).get('day', [])
    if not isinstance(days, list):
        days = [days]  # Wenn nur ein Tag vorhanden ist

    result = []

    for day in days:
        date = day.get('@date')
        categories = day.get('category', [])
        if not isinstance(categories, list):
            categories = [categories]

        for category in categories:
            cat_name = category.get('@name')
            meals = category.get('meal', [])
            if not isinstance(meals, list):
                meals = [meals]

            for meal in meals:
                name = meal.get('name')
                notes = meal.get('note', [])
                if isinstance(notes, str):
                    notes = [notes]

                prices = {}
                for price in meal.get('price', []):
                    role = price.get('@role')
                    value = float(price.get('#text', 0))
                    prices[role] = value

                result.append({
                    'date': date,
                    'category': cat_name,
                    'name': name,
                    'notes': notes,
                    'prices': prices
                })

    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
