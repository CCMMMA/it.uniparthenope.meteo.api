"""CMS access helpers used by the version 2 endpoints."""

# import pymongo
# import core.MongoDbHandlers
from core.MongoDbHandlers import MongoDBHandlers


class CMS(object):
    """Service or helper that encapsulates cms behavior."""
    conf = {}

    def __init__(self, cfg):
        """Initialize cms state."""
        self.conf = cfg

    def get_carousel(self, roles, options=None):
        """Return carousel."""
        result = []

        lang = self.conf["LANG"]
        # conn = pymongo.MongoClient()
        # db = conn[self.cfg['DATABASE']]
        # carousel = db['carousel']

        if options is not None:
            if "lang" in options and options['lang'] is not None:
                lang = options['lang']

        # items = carousel.find(
        #    {"roles.view": {"$in": roles}, "active": True},
        #    {"_id": 1, "avail": 1, "i18n." + lang: 1}).sort([("order", pymongo.ASCENDING)])

        # items = MongoDBHandlers.get_query(
        #    'carousel', {"roles.view": {"$in": roles}, "active": True}, {"_id": 1, "avail": 1, "i18n." + lang: 1}).sort([("order", pymongo.ASCENDING)]))

        items = MongoDBHandlers(self.conf).get_query('carousel', {"roles.view": {"$in": roles}, "active": True}, {"_id": 1, "avail": 1, "i18n." + lang: 1}, order_flag=True)

        for item in items:

            if "roles" in item:
                del item["roles"]

            result.append(item)
        # conn.close()
        return result

    def get_cards(self, roles, options=None):
        """Return cards."""
        result = []
        lang = self.conf["LANG"]
        # conn = pymongo.MongoClient()
        # db = conn[self.cfg['DATABASE']]
        # cards = db['cards']

        if options is not None:
            if "lang" in options and options['lang'] is not None:
                lang = options['lang']

        # items = cards.find(
        #    {"roles.view": {"$in": roles}, "active": True},
        #    {"_id": 1, "avail": 1, "i18n." + lang: 1}).sort([("order", pymongo.ASCENDING)])

        items = MongoDBHandlers(self.conf).get_query('cards', {"roles.view": {"$in": roles}, "active": True}, {"_id": 1, "avail": 1, "i18n." + lang: 1}, order_flag=True)

        for item in items:

            if "roles" in item:
                del item["roles"]

            result.append(item)
        # conn.close()
        return result
