"""Worker-pool helpers for parallel processing tasks."""

#################################################
#   
#   Università Degli Studi di Napoli Parthenope 
#
#
# Author: 
#    Dario Caramiello   
#
#################################################

import threading

from requests import Session
from core.Logger import logger

# One session per thread: worker processes use only their main thread, while
# thread-pool workers must not share a Session, which is not thread-safe.
_local = threading.local()

def _init_session():
    """Initialize a reusable HTTP session for the calling worker."""
    session = Session()

    session.verify = False

    from urllib3.util.retry import Retry
    from requests.adapters import HTTPAdapter

    retry = Retry(
        total=5,                 # n. max di retry complessivi
        backoff_factor=0.5,      # attesa esponenziale: 0.5, 1, 2, 4, ...
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD","GET","POST","PUT","DELETE","OPTIONS","TRACE"]
    )

    adapter = HTTPAdapter(
        pool_connections=100,    # connessioni per host tenute vive
        pool_maxsize=100,        # max socket in pool (x host) usabili in parallelo
        max_retries=retry        # strategia di retry definita sopra
    )

    session.mount("http://", adapter)
    session.mount("https://", adapter)

    _local.session = session
    return session


def work_worker(method: str, url: str, *, json=None, params=None, headers=None, timeout=(5, 60)):
    """Execute one worker task and return its processed result."""
    session = getattr(_local, "session", None)
    if session is None:
        session = _init_session()

    response = session.request(method, url, json=json, params=params, headers=headers, timeout=timeout)
    logger.info("response.url : %s", response.url)
    response.raise_for_status()
    return response.json()

def dispatch(m, u, kw):
    """Dispatch work items across the configured worker pool."""
    return work_worker(m, u, **kw)
