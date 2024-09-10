# import pymongo
# import core.MongoDbHandlers
from core.MongoDbHandlers import MongoDBHandlers


class CMS(object):
    conf = {}

    def __init__(self, cfg):
        self.conf = cfg

    def get_navbar(self, roles, options=None):
        result = []
        lang = self.conf["LANG"]
        # conn = pymongo.MongoClient()g
        # db = conn[self.conf['DATABASE']]
        # navbar_menu_items = db['navbar_menu_items']

        if options is not None:
            if "lang" in options and options['lang'] is not None:
                lang = options['lang']

            if "userId" in options and options['userId'] is not None:
                userId = options['userId']

        # menu_items = navbar_menu_items.find({
        #    "roles.view": {"$in": roles}
        # }, {
        #    "_id": 1,
        #    "i18n." + lang: 1,
        # }).sort([("order", pymongo.ASCENDING)])

        menu_items = MongoDBHandlers(self.conf).get_query('navbar_menu_items',
                                                          {"roles.view": {"$in": roles}},
                                                          {"_id": 1, "i18n." + lang: 1})

        for menu_item in menu_items:

            if "items" in menu_item["i18n"][lang]:
                submenu_items = menu_item["i18n"][lang]["items"]
                submenu_items_to_remove = []
                for submenu_item in submenu_items:

                    if "roles" in submenu_item:
                        if not set(roles).intersection(set(submenu_item["roles"]['view'])):
                            submenu_items_to_remove.append(submenu_item)
                        else:
                            del submenu_item["roles"]

                for submenu_item in submenu_items_to_remove:
                    submenu_items.remove(submenu_item)

            result.append(menu_item)
        # conn.close()
        return result

    def get_pages(self, roles, options=None):
        result = []

        lang = self.conf["LANG"]
        # conn = pymongo.MongoClient()
        # db = conn[self.conf['DATABASE']]
        # pages = db['pages']

        if options is not None:
            if "lang" in options and options['lang'] is not None:
                lang = options['lang']

            if "userId" in options and options['userId'] is not None:
                userId = options['userId']

        # items = pages.find({}, {"_id": 1, "author": 1, "i18n." + lang + ".title": 1})  # .sort( { "_id": 1 } )
        items = MongoDBHandlers(self.conf).get_query('pages', {}, {"_id": 1, "author": 1,
                                                                   "i18n." + lang + ".title": 1})
        for item in items:
            result.append(item)
        # conn.close()
        return result

    def set_page_by_id(self, roles, _id, payload, options=None):
        # print(str(payload))
        # print(str(options))
        retval = {"errMsg": "Stub ok"}
        return retval

    def get_page_by_id(self, roles, _id, options=None):
        # Set the userId
        userId = None

        # Set the default language
        lang = self.conf["LANG"]

        db_instance = MongoDBHandlers(self.conf)
        # Open the database
        # conn = pymongo.MongoClient()

        # Select the database
        # db = conn[self.conf['DATABASE']]

        # Select the page collection
        # pages = db['pages']

        # Check if a language is specified
        if options is not None:
            if "lang" in options and options['lang'] is not None:
                lang = options['lang']

            if "userId" in options and options['userId'] is not None:
                userId = options['userId']

        # Search for the page
        # result = pages.find_one({"_id": _id, "active": True}, {"_id": 1, "roles": 1, "author": 1, "i18n." + lang: 1})

        result = db_instance.get_query_find_one('pages',
                                                {"_id": _id, "active": True},
                                                {"_id": 1, "roles": 1, "author": 1,
                                                 "i18n." + lang: 1})

        # Check if the page is available
        if result is not None:

            result["permissions"] = []

            if set(roles).intersection(set(result["roles"]["view"])):
                # Can view
                result["permissions"].append("view")

                # Check if can edit
                if set(roles).intersection(set(result["roles"]["edit"])):
                    # Can edit
                    result["permissions"].append("edit")

                # Check if can delete
                if set(roles).intersection(set(result["roles"]["delete"])):
                    # Can delete
                    result["permissions"].append("delete")

            else:

                # Return a 403 like page.
                # result = pages.find_one({"_id": "page403"}, {"_id": 1, "author": 1, "i18n." + lang: 1})
                result = db_instance.get_query_find_one('pages', {"_id": "page403"},
                                                        {"_id": 1, "author": 1, "i18n." + lang: 1})


        else:
            # Return a 404 like page.
            # result = pages.find_one({"_id": "page404"}, {"_id": 1, "author": 1, "i18n." + lang: 1})
            result = db_instance.get_query_find_one('pages', {"_id": "page404"},
                                                    {"_id": 1, "author": 1, "i18n." + lang: 1})

        # Protect the roles attribute
        if result is not None and "roles" in result:
            # Remove the roles field from the output
            del result["roles"]

            # Close the db connection
        #conn.close()

        # Return the result
        return result

    def get_carousel(self, roles, options=None):
        result = []

        lang = self.conf["LANG"]
        # conn = pymongo.MongoClient()
        # db = conn[self.cfg['DATABASE']]
        # carousel = db['carousel']

        if options is not None:
            if "lang" in options and options['lang'] is not None:
                lang = options['lang']

            if "userId" in options and options['userId'] is not None:
                userId = options['userId']

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
        result = []
        userId = None

        lang = self.conf["LANG"]
        # conn = pymongo.MongoClient()
        # db = conn[self.cfg['DATABASE']]
        # cards = db['cards']

        if options is not None:
            if "lang" in options and options['lang'] is not None:
                lang = options['lang']

            if "userId" in options and options['userId'] is not None:
                userId = options['userId']

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
