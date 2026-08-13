"""MongoDB access helpers for place and metadata queries."""

import pymongo.errors
from core.Logger import logger

class MongoDBHandlers(object):
    """Service or helper that encapsulates mongo dbhandlers behavior."""
    config = {}

    def __init__(self, config):
        """Initialize mongo dbhandlers state."""
        self.config = config

    def get_query(self, name_collection, query=None, proj=None, limit=None, order_flag=None, all_places=False):
        """Return query."""
        out = []
        try:
            client = pymongo.MongoClient("mongodb://db:27017/", connect=False)
        except pymongo.errors.ConnectionFailure as connection_failure:
            logger.error(str(connection_failure))
        except pymongo.errors.ConfigurationError as configuration_error:
            logger.error(str(configuration_error))
        db = client[self.config['DATABASE']]
        collection = db[name_collection]
        if all_places is True:
            return list(collection.find())
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
        """Return query find one."""
        try:
            client = pymongo.MongoClient("mongodb://db:27017/", connect=False)
        except pymongo.errors.ConnectionFailure as connection_failure:
            logger.error(str(connection_failure))
        except pymongo.errors.ConfigurationError as configuration_error:
            logger.error(str(configuration_error))
        db = client[self.config['DATABASE']]
        collection = db[name_collection]
        out = collection.find_one(query, proj)
        client.close()
        return out

    def call_insert_one(self, name_collection, data):
        """Implement call insert one for mongo dbhandlers."""
        try:
            client = pymongo.MongoClient("mongodb://db:27017/", connect=False)
        except pymongo.errors.ConnectionFailure as connection_failure:
            logger.error(str(connection_failure))
        except pymongo.errors.ConfigurationError as configuration_error:
            logger.error(str(configuration_error))
        db = client[self.config['DATABASE']]
        collection = db[name_collection]
        out = collection.insert_one(data)
        client.close()
        return out
