#################################################
#   
#   Università Degli Studi di Napoli Parthenope 
#
#
# Author: 
#    Dario Caramiello   
#
#################################################

from requests import Session
from core.Logger import logger
import certifi 

_session = None

def _init_session():
    global _session
    _session = Session()

    _session.verify = False

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

    _session.mount("http://", adapter)
    _session.mount("https://", adapter)

    return _session


def work_worker(method: str, url: str, *, json=None, params=None, headers=None, timeout=(5, 60)):
    global _session
    if not _session:
        _session = _init_session()
    
    response = _session.request(method, url, json=json, params=params, headers=headers, timeout=timeout)
    logger.info(f"response.url : {response.url}")
    response.raise_for_status()

    # try:
        #return response.status_code, response.json()
    return response.json()
    # except ValueError:
        # return response.status_code, response.text
        #return response.text

def dispatch(m, u, kw):
    return work_worker(m, u, **kw)