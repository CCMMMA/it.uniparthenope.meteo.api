class Box(object):

    def get_today(self, params):
        result = {
            "placeLabel": "Provincia di NAPOLI",
            "placeUrl": "http:\/\/ccmmma.uniparthenope.it\/?q=forecast\/weather&region=prov063",
            "days":
                [
                    {
                        "dayDateLabel": "10\/03\/2014",
                        "utcDateTime": "20140310Z00",
                        "weekDayLabel": "Luned&igrave;",
                        "monthDay": "10",
                        "wiconurl": "http:\/\/ccmmma.uniparthenope.it\/sites\/all\/modules\/home_page\/icons\/new\/cloudy1.png",
                        "wtextLabel": "Poco nuvoloso", "tMin": "10&degC", "tMax": "14&degC", "wd10Label": "ENE",
                        "ws10": "13 knt", "crh": "0.6 mm", "slp": "1016Hpa", "rh2": "0%",
                        "waveLabel": " - Mare Poco mosso da ESE di 0.4m (4 s)",
                        "ws10Label": "Vento moderato"
                    },
                    {
                        "dayDateLabel": "11\/03\/2014", "utcDateTime": "20140311Z00", "weekDayLabel": "Marted&igrave;",
                        "monthDay": "11",
                        "wiconurl": "http:\/\/ccmmma.uniparthenope.it\/sites\/all\/modules\/home_page\/icons\/new\/cloudy1.png",
                        "wtextLabel": "Poco nuvoloso",
                        "tMin": "10&degC",
                        "tMax": "14&degC",
                        "wd10Label": "NE",
                        "ws10": "13 knt",
                        "crh": "0.5 mm",
                        "slp": "1020Hpa",
                        "rh2": "0%",
                        "waveLabel": " - Mare Poco mosso da WSW di 0.17m (4 s)",
                        "ws10Label": "Vento moderato"
                    },
                    {
                        "dayDateLabel": "12\/03\/2014",
                        "utcDateTime": "20140312Z00",
                        "weekDayLabel": "Mercoled&igrave;",
                        "monthDay": "12",
                        "wiconurl": "http:\/\/ccmmma.uniparthenope.it\/sites\/all\/modules\/home_page\/icons\/new\/sunny.png",
                        "wtextLabel": "Sereno",
                        "tMin": "9&degC",
                        "tMax": "15&degC",
                        "wd10Label": "ENE",
                        "ws10": "9 knt",
                        "crh": "-",
                        "slp": "1027Hpa",
                        "rh2": "0%",
                        "waveLabel": " - Mare Poco mosso da SSE di 0.23m (3 s)",
                        "ws10Label": "Brezza tesa"
                    },
                    {
                        "dayDateLabel": "13\/03\/2014",
                        "utcDateTime": "20140313Z00",
                        "weekDayLabel": "Gioved&igrave;",
                        "monthDay": "13",
                        "wiconurl": "http:\/\/ccmmma.uniparthenope.it\/sites\/all\/modules\/home_page\/icons\/new\/sunny.png",
                        "wtextLabel": "Sereno", "tMin": "10&degC", "tMax": "16&degC", "wd10Label": "ENE",
                        "ws10": "10 knt",
                        "crh": "-",
                        "slp": "1028Hpa",
                        "rh2": "0%",
                        "waveLabel": " - Mare Quasi calmo da WNW di 0.09m (4 s)",
                        "ws10Label": "Brezza tesa"
                    },
                    {
                        "dayDateLabel": "14\/03\/2014",
                        "utcDateTime": "20140314Z00",
                        "weekDayLabel": "Venerd&igrave;",
                        "monthDay": "14",
                        "wiconurl": "http:\/\/ccmmma.uniparthenope.it\/sites\/all\/modules\/home_page\/icons\/new\/sunny.png",
                        "wtextLabel": "Sereno",
                        "tMin": "10&degC",
                        "tMax": "15&degC",
                        "wd10Label": "NE",
                        "ws10": "3 knt",
                        "crh": "-",
                        "slp": "1029Hpa",
                        "rh2": "0%",
                        "waveLabel": " - Mare Poco mosso da WSW di 0.15m (4 s)",
                        "ws10Label": "Bava di vento"
                    },
                    {
                        "dayDateLabel": "15\/03\/2014",
                        "utcDateTime": "20140315Z00",
                        "weekDayLabel": "Sabato",
                        "monthDay": "15",
                        "wiconurl": "http:\/\/ccmmma.uniparthenope.it\/sites\/all\/modules\/home_page\/icons\/new\/sunny.png",
                        "wtextLabel": "Sereno",
                        "tMin": "10&degC",
                        "tMax": "15&degC",
                        "wd10Label": "NW",
                        "ws10": "3 knt",
                        "crh": "-",
                        "slp": "1025Hpa",
                        "rh2": "0%",
                        "waveLabel": " - Mare Poco mosso da WSW di 0.11m (7 s)",
                        "ws10Label": "Bava di vento"
                    }
                ]
        }
        return result


# if __name__ == "__main__":
#    box = Box()
#    print(box.get_today())
