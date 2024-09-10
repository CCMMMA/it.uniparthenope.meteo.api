import feedparser
from flask import jsonify


def get_field_lwr_jsonify(field):
    news_feed = feedparser.parse("https://meteo.uniparthenope.it/rss/weatherreports")
    entry = news_feed.entries[0]

    latest_field_weather_report = {
        field: str(entry[field].encode('utf8'))
    }

    return jsonify(latest_field_weather_report)


def get_latest_weather_report_jsonify():
    news_feed = feedparser.parse("https://meteo.uniparthenope.it/rss/weatherreports")
    # le entries rappresentano un elenco ordinato come appare nel feed.
    # consideriamo la entries[0] corrisponde alla prima previsione , ovvero quella piu recente

    # nella versione originale dava un errore rispetto ad un oggetto di tipo byte non poteva essere serializzato
    # in JSON. l oggetto in questione corrisponde al risultato dell encode('utf-8').
    # risolto : una volta codificata la string an formato utf-8 la trasformo in string.
    # quindi la stringa conterra gli stessi caratteri del formato utf-8 ma con la differenza che adesso
    # non e un oggetto byte ma string , e puo essere serializzato.

    # eliminato variabili e accesso diretto ai campi interessati della struttura
    latest_weather_report = {
        "published": news_feed.entries[0].published,
        "i18n": {
            "it-IT": {
                "title": news_feed.entries[0].title,
                "summary": news_feed.entries[0].summary
            },
            "en-US": {
                "title": str(news_feed.entries[0].title.encode('utf-8')),
                "summary": str(news_feed.entries[0].summary.encode('utf8'))
            }
        }
    }
    # print(str(news_feed.entries[0].title.encode('utf-8')))
    return jsonify(latest_weather_report)


def get_all_weather_reports_jsonify():
    # sanitizer = Sanitizer()
    news_feed = feedparser.parse("https://meteo.uniparthenope.it/rss/weatherreports")
    weather_reports = []

    for entry in news_feed.entries:
        weather_reports.append({
            "published": entry.published,
            "i18n": {
                "it-IT": {
                    "title": str(entry.title.encode('utf-8')),
                    "summary": str(entry.summary.encode('utf-8'))
                },
                "en-US": {
                    "title": str(entry.title.encode('utf-8')),
                    "summary": str(entry.summary.encode('utf-8'))
                },
                "link": entry.link
            }
        })

        return jsonify({"entries": weather_reports})
