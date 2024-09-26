import logging
from logging.config import dictConfig

dictConfig({
    'version': 1,
    'formatters': {
        'default': {
            'format': '%(levelname)s: %(message)s',
        },
        'info_format': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s (function [ %(funcName)s ]) (line [ %(lineno)d ]): %(message)s ',
            # 'format': '[%(asctime)s] %(levelname)s in %(module)s (%(funcName)s): %(message)s',
        },
        'error_format': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s (function [ %(funcName)s ]) (line [ %(lineno)d ]): %(message)s ',
        },
        'warning_format': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s (function [ %(funcName)s ]) (line [ %(lineno)d ]): %(message)s ',
        },
        "critical_format": {
            'format': '[%(asctime)s] %(levelname)s in %(module)s (function [ %(funcName)s ]) (line [ %(lineno)d ]): %(message)s '
        }
    },
    'handlers': {
        #'wsgi': {
        #    'class': 'logging.StreamHandler',
        #    'stream': 'ext://flask.logging.wsgi_errors_stream',
        #    'formatter': 'default'
        #},
        'info_handler': {
            'class': 'logging.StreamHandler',
            'formatter': 'info_format',
            'level': 'INFO',
        },
        'error_handler': {
            'class': 'logging.StreamHandler',
            'formatter': 'error_format',
            'level': 'ERROR',
        },
        'warning_handler': {
            'class': 'logging.StreamHandler',
            'formatter': 'warning_format',
            'level': 'WARNING',
        },
        'critical_handler': {
            'class': 'logging.StreamHandler',
            'formatter': 'critical_format',
            'level': 'CRITICAL',
        }
    },
    'loggers': {
        'main_logger': {
            'level': 'DEBUG',
            'handlers': ['info_handler', 'error_handler', 'warning_handler', 'critical_handler'],
            'propagate': False
        }
    }
    #'root': {
    #    'level': 'INFO',
    #    'handlers': ['wsgi']
    #}
})

logger = logging.getLogger('main_logger')