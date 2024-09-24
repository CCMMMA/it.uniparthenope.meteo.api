import pymongo.errors
# import logging

#### Logging ####
# log = logging.getLogger(__name__)
# hdlr = logging.FileHandler('var/log/test.log')
# formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
# hdlr.setFormatter(formatter)
# log.addHandler(hdlr)
# log.setLevel(logging.INFO)
################

class MongoDBHandlers(object):
    config = {}

    def __init__(self, config):
        self.config = config

    def get_query(self, name_collection, query, proj, limit=None, order_flag=None):
        out = []
        try:
            client = pymongo.MongoClient("mongodb://db:27017/", connect=False)
        except pymongo.errors.ConnectionFailure as connection_failure:
            log.error(str(connection_failure))
        except pymongo.errors.ConfigurationError as configuration_error:
            log.error(str(configuration_error))
        db = client[self.config['DATABASE']]
        collection = db[name_collection]
        if limit is None:
            for item in collection.find(query, proj):
                out.append(item)
        else:
            for item in collection.find(query, proj).limit(limit):
                out.append(item)
        if order_flag is not None:
            return collection.find(query, proj).sort([("order", pymongo.ASCENDING)])
        client.close()
        return out

    def get_query_find_one(self, name_collection, query, proj):
        try:
            client = pymongo.MongoClient("mongodb://db:27017/", connect=False)
        except pymongo.errors.ConnectionFailure as connection_failure:
            print(str(connection_failure))
            # log.error(str(connection_failure))
        except pymongo.errors.ConfigurationError as configuration_error:
            print(str(configuration_error))
            # log.error(str(configuration_error))
        db = client[self.config['DATABASE']]
        collection = db[name_collection]
        out = collection.find_one(query, proj)
        client.close()
        return out

    def call_insert_one(self, name_collection, data):
        try:
            client = pymongo.MongoClient("mongodb://db:27017/", connect=False)
        except pymongo.errors.ConnectionFailure as connection_failure:
            print(str(connection_failure))
            # log.error(str(connection_failure))
        except pymongo.errors.ConfigurationError as configuration_error:
            print(str(configuration_error))
            # log.error(str(configuration_error))
        db = client[self.config['DATABASE']]
        collection = db[name_collection]
        out = collection.insert_one(data)
        client.close()
        return out
