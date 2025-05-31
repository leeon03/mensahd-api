from flask import Flask, jsonify, request
from mannheim import getParser  # Passe den Import an deinen Modulnamen an
import xmltodict
import logging

app = Flask(__name__)
parser = getParser("http://localhost:8080/{metaOrFeed}/{mensaReference}.xml")

@app.route('/api/mensa/<ref>')
def get_mensa_data(ref):
    # Anzahl Tage per URL-Parameter, z.B. /api/mensa/schloss?days=30
    try:
        days = int(request.args.get('days', 21))
    except ValueError:
        days = 21

    # Feed generieren
    xml = parser.feed(ref, days)
    data = xmltodict.parse(xml)

    days_data = data.get('openmensa', {}).get('canteen', {}).get('day', [])
    if not isinstance(days_data, list):
        days_data = [days_data]

    result = []
    for day in days_data:
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

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    from waitress import serve
    serve(app, host="0.0.0.0", port=8080)
