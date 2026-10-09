"""MongoDB access helpers for place and metadata queries."""

import os
import threading

import pymongo
import pymongo.errors
from core.Logger import logger

_DEFAULT_MONGODB_URI = "mongodb://db:27017/"

# MongoClient owns a thread-safe connection pool, so one instance per process
# and URI serves every request. The pid is part of the key because a client
# must not be reused across fork().
_clients = {}
_clients_lock = threading.Lock()


def _get_client(uri):
    """Return the shared MongoClient of the current process for one URI."""
    key = (os.getpid(), uri)
    client = _clients.get(key)
    if client is None:
        with _clients_lock:
            client = _clients.get(key)
            if client is None:
                client = pymongo.MongoClient(uri, connect=False)
                _clients[key] = client
    return client


class MongoDBHandlers(object):
    """Service or helper that encapsulates mongo dbhandlers behavior."""
    config = {}

    def __init__(self, config):
        """Initialize mongo dbhandlers state."""
        self.config = config

    def _collection(self, name_collection):
        """Return a collection handle backed by the shared client."""
        uri = self.config.get("MONGODB_URI", _DEFAULT_MONGODB_URI)
        try:
            client = _get_client(uri)
        except pymongo.errors.PyMongoError as mongo_error:
            logger.error(str(mongo_error))
            raise
        return client[self.config['DATABASE']][name_collection]

    def get_query(self, name_collection, query=None, proj=None, limit=None, order_flag=None, all_places=False):
        """Return query."""
        collection = self._collection(name_collection)
        if all_places is True:
            return list(collection.find())
        if order_flag is not None:
            return collection.find(query, proj).sort([("order", pymongo.ASCENDING)])
        cursor = collection.find(query, proj)
        if limit is not None:
            cursor = cursor.limit(limit)
        return list(cursor)

    def get_query_find_one(self, name_collection, query, proj):
        """Return query find one."""
        return self._collection(name_collection).find_one(query, proj)

    def call_insert_one(self, name_collection, data):
        """Implement call insert one for mongo dbhandlers."""
        return self._collection(name_collection).insert_one(data)
