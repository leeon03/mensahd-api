import sys
import os
import re
import json
import datetime
import requests
import logging
import urllib
import urllib.parse
import bs4

try:
    from version import __version__, useragentname, useragentcomment
    from util import StyledLazyBuilder, now_local, xml_escape, meta_from_xsl, xml_str_param
except ModuleNotFoundError:
    include = os.path.relpath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, include)
    from version import __version__, useragentname, useragentcomment
    from util import StyledLazyBuilder, now_local, xml_escape, meta_from_xsl, xml_str_param


class Parser:
    canteen_json = os.path.join(os.path.dirname(__file__), "canteens.json")
    meta_xslt = os.path.join(os.path.dirname(__file__), "../meta.xsl")
    feed_xslt = os.path.join(os.path.dirname(__file__), "feed.xsl")
    headers = {
        'User-Agent': f'{useragentname}/{__version__} ({useragentcomment}) {requests.utils.default_user_agent()}'
    }

    source_url = "https://www.stw-ma.de/essen-trinken/speiseplaene/wochenansicht"
    source_parameters = "?location={location}&date={year}-{month}-{day}&lang=de"
    source_parameters_meta = "?location={location}&lang=de"

    def correct_capitalization(self, s): return s[0].upper() + s[1:].lower()

    day_regex = re.compile(r'(?P<date>\d{2}\.\d{2}\.\d{4})')
    removeextras_regex = re.compile(r'\s+\[(\w,?)+\]')
    price_regex = re.compile('Bedienstete \\+ (?P<employee>\\d+)\\%, Gäste \\+ (?P<guest>\\d+)\\%')
    euro_regex = re.compile(r'(\d+,\d+) €')
    whitespace = re.compile(r'\s+')
    weekdays = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    roles = ('student', 'employee', 'other')

    def feed(self, ref: str, days: int = 21) -> str:
        if ref not in self.canteens:
            return f"Unknown canteen with ref='{xml_escape(ref)}'"

        if "loc" not in self.canteens[ref]:
            return f"Canteen with ref='{xml_escape(ref)}' has no loc-id"

        canteen = StyledLazyBuilder()

        for offset in range(days):
            day = now_local().date() + datetime.timedelta(days=offset)
            if day.weekday() == 6:
                continue

            url = self.source_url + self.source_parameters.format(
                location=self.canteens[ref]["loc"],
                year=day.strftime('%Y'),
                month=day.strftime('%m'),
                day=day.strftime('%d')
            )

            try:
                content = requests.get(url, headers=self.headers).text
            except requests.exceptions.ConnectionError as e:
                logging.warning(e)
                content = requests.get(url, headers=self.headers, verify=False).text

            content = content.replace("</th>", "</td>").replace("<th ", "<td ")
            document = bs4.BeautifulSoup(content, "html.parser")

            from_tag = document.find("h2")
            if not from_tag:
                canteen.setDayClosed(day)
                continue

            try:
                fromMatch = self.day_regex.search(from_tag.text.strip()).group("date")
                fromDatetime = datetime.datetime.strptime(fromMatch, "%d.%m.%Y")
            except Exception:
                canteen.setDayClosed(day)
                continue

            legend = {}
            for span in document.select("#legend>span"):
                sup = span.find("sup")
                if sup and sup.text:
                    key = sup.text.strip()
                    sup.clear()
                    value = span.text.strip()
                    legend[key] = value

            try:
                p = self.price_regex.search(document.find("p", {"id": "message"}).text).groupdict()
                employee_multiplier = 1.0 + int(p["employee"]) / 100.0
                guest_multiplier = 1.0 + int(p["guest"]) / 100.0
            except Exception:
                employee_multiplier = 1.25
                guest_multiplier = 1.60

            table = document.find("table", {"id": "previewTable"})
            if not table or not isinstance(table, bs4.Tag):
                canteen.setDayClosed(day)
                continue

            trs = table.find_all("tr")
            canteenCategories = []
            firstTr = True
            previous = None

            for tr in trs:
                closed = False
                mealsFound = False
                if firstTr:
                    firstTr = False
                    for th in tr.find_all("td")[1:]:
                        canteenCategories.append(th.text.strip())
                elif previous is None:
                    previous = tr
                else:
                    datetd = previous.find("td", {"class": "first"})
                    weekday = datetd.text.strip()
                    date = fromDatetime
                    i = 0
                    while self.weekdays.index(weekday) != date.weekday() and i < 8:
                        date += datetime.timedelta(days=1)
                        i += 1
                    if i > 7:
                        logging.error(f"Date could not be calculated from {weekday!r}")
                    date = date.date()

                    if len(previous.find_all("td")) < 2 or "geschlossen" in previous.find_all("td")[1].text.strip().lower():
                        closed = date

                    cat = 0
                    for td0, td1 in zip(previous.find_all("td")[1:], tr.find_all("td")):
                        raw_text = td0.get_text(separator=" ", strip=True)
                        if "kein angebot" in raw_text.lower() or "geschlossen" in raw_text.lower():
                            cat += 1
                            continue

                        notes = set()
                        if td0.find("h2"):
                            categoryName = canteenCategories[cat] + " " + self.correct_capitalization(td0.find("h2").text.strip())
                        else:
                            categoryName = canteenCategories[cat]

                        if "Kubusangebote am Themenpark" in td0.text:
                            canteen.addMeal(date, categoryName, "Kubusangebote am Themenpark", [])
                            cat += 1
                            continue

                        for sup in td0.find_all("sup"):
                            keep = []
                            for a in sup.text.strip("()").split(","):
                                if a == "Veg":
                                    keep.append("🥕")
                                    notes.add("🥕 = Vegetarisch")
                                elif a == "Vga":
                                    keep.append("🌿")
                                    notes.add("🌿 = Vegan")
                                elif a == "Bio":
                                    keep.append("♻️")
                                    notes.add("♻️ = Bio")
                                elif a and a in legend:
                                    notes.add(legend[a])
                                elif a:
                                    notes.add(a)
                            sup.clear()
                            if keep:
                                sup.append("%s" % (",".join(keep),))

                        name = self.whitespace.sub(" ", raw_text).strip().replace(" ,", ",")
                        if not name or name.lower() in ["", "geschlossen", "kein angebot"]:
                            logging.warning(f"Übersprungene Zeile ohne Namen: '{td0}'")
                            cat += 1
                            continue

                        prices = []
                        spans = td1.find_all("span", {"class": "label"})
                        if spans:
                            try:
                                price = float(self.euro_regex.search(spans[0].text).group(1).replace(",", "."))
                                prices = (price, price * employee_multiplier, price * guest_multiplier)
                            except Exception:
                                notes.add(spans[0].text.strip() + " Preis")

                            if len(spans) == 2:
                                notes.add(spans[1].text.strip() + " Preis")

                        canteen.addMeal(date, categoryName, name, notes, prices, self.roles if prices else None)
                        mealsFound = True
                        cat += 1

                    previous = None
                    if not mealsFound and closed:
                        canteen.setDayClosed(closed)

        return canteen.toXMLFeed()

    def meta(self, ref):
        if ref not in self.canteens:
            return f"Unknown canteen with ref='{xml_escape(ref)}'"
        mensa = self.canteens[ref]

        data = {
            "name": xml_str_param(mensa["name"]),
            "address": xml_str_param(mensa["address"]),
            "city": xml_str_param(mensa["city"]),
            "latitude": xml_str_param(mensa["latitude"]),
            "longitude": xml_str_param(mensa["longitude"]),
            "feed": xml_str_param(self.url_template.format(metaOrFeed='feed', mensaReference=urllib.parse.quote(ref))),
            "source": xml_str_param(self.source_url + self.source_parameters_meta.format(location=self.canteens[ref]["loc"])),
        }

        if "phone" in mensa:
            data["phone"] = xml_str_param(mensa["phone"])
        if "times" in mensa:
            data["times"] = mensa["times"]

        return meta_from_xsl(self.meta_xslt, data)

    def __init__(self, url_template):
        with open(self.canteen_json, 'r', encoding='utf8') as f:
            self.canteens = json.load(f)
        self.url_template = url_template

    def json(self):
        tmp = {}
        for reference in self.canteens:
            tmp[reference] = self.url_template.format(
                metaOrFeed='meta', mensaReference=urllib.parse.quote(reference))
        return json.dumps(tmp, indent=2)


def getParser(url_template):
    return Parser(url_template)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    p = Parser("http://localhost/{metaOrFeed}/mannheim_{mensaReference}.xml")
    print(p.feed("schloss"))
    print(p.meta("schloss"))
