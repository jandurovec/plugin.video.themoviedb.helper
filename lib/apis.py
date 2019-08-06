import requests
import utils
from utils import kodi_log
import xbmcgui
import datetime
import simplecache
import time
import xml.etree.ElementTree as ET
from globals import TMDB_API, _tmdb_apikey, _language, OMDB_API, _omdb_apikey, OMDB_ARG, _addonname, _waittime
_cache = simplecache.SimpleCache()


def my_rate_limiter(func):
    """
    Simple rate limiter
    """
    def decorated(*args, **kwargs):
        nart_time_id = _addonname + 'nart_time_id'
        nart_lock_id = _addonname + 'nart_lock_id'
        # Get our saved time value
        nart_time = xbmcgui.Window(10000).getProperty(nart_time_id)
        # If no value set to -1 to skip rate limiter
        nart_time = float(nart_time) if nart_time else -1
        nart_time = nart_time - time.time()
        # Apply rate limiting if next allowed request time is still in the furture
        if nart_time > 0:
            nart_lock = xbmcgui.Window(10000).getProperty(nart_lock_id)
            # If another instance is applying rate limiting then wait till it finishes
            while nart_lock == 'True':
                time.sleep(1)
                nart_lock = xbmcgui.Window(10000).getProperty(nart_lock_id)
            # Get the nart again because it might have elapsed
            nart_time = xbmcgui.Window(10000).getProperty(nart_time_id)
            nart_time = float(nart_time) if nart_time else -1
            nart_time = nart_time - time.time()
            # If nart still in the future then apply rate limiting
            if nart_time > 0:
                # Set the lock so another rate limiter cant run at same time
                xbmcgui.Window(10000).setProperty(nart_lock_id, 'True')
                while nart_time > 0:
                    time.sleep(1)
                    nart_time = nart_time - 1
        # Set nart into future for next request
        nart_time = time.time() + _waittime
        nart_time = str(nart_time)
        # Set the nart value
        xbmcgui.Window(10000).setProperty(nart_time_id, nart_time)
        # Unlock rate limiter so next instance can run
        xbmcgui.Window(10000).setProperty(nart_lock_id, 'False')
        # Run our function
        return func(*args, **kwargs)
    return decorated


def use_mycache(cache_days=14, suffix=''):
    def decorator(func):
        def decorated(*args, **kwargs):
            cache_name = _addonname
            if suffix:
                cache_name = cache_name + '/' + suffix
            for arg in args:
                if arg:
                    cache_name = cache_name + '/' + arg
            for key, value in kwargs.items():
                if value:
                    cache_name = cache_name + '&' + key + '=' + value
            my_cache = _cache.get(cache_name)
            if my_cache:
                kodi_log('CACHE REQUEST:\n' + cache_name)
                return my_cache
            else:
                kodi_log('API REQUEST:\n' + cache_name)
                my_objects = func(*args, **kwargs)
                _cache.set(cache_name, my_objects, expiration=datetime.timedelta(days=cache_days))
                return my_objects
        return decorated
    return decorator


@my_rate_limiter
def make_request(request, is_json):
    request_type = 'OMDb' if OMDB_API in request else 'TMDb'
    kodi_log('Requesting... ' + request, 1)
    request = requests.get(request)  # Request our data
    if not request.status_code == requests.codes.ok:  # Error Checking
        if request.status_code == 401:
            kodi_log('HTTP Error Code: ' + str(request.status_code), 1)
            utils.invalid_apikey(request_type)
            exit()
        else:
            kodi_log('HTTP Error Code: ' + str(request.status_code), 1)
    if is_json:
        request = request.json()  # Make the request nice
    return request


@use_mycache(1, 'tmdb_api')
def tmdb_api_request(*args, **kwargs):
    """
    Request from TMDb API and store in cache for 24 hours
    Use when requesting lists that change regular (e.g. Popular / Airing etc.)
    """
    request = TMDB_API
    for arg in args:
        if arg:  # Don't add empty args
            request = request + '/' + arg
    request = request + _tmdb_apikey + _language
    for key, value in kwargs.items():
        if value:  # Don't add empty kwargs
            request = request + '&' + key + '=' + value
    request = make_request(request, True)
    return request


@use_mycache(14, 'tmdb_api')
def tmdb_api_request_longcache(*args, **kwargs):
    """
    Request from TMDb API and store in cache for 14 days
    Use when requesting movie details or other info that doesn't change regularly
    """
    return tmdb_api_request(*args, **kwargs)


@use_mycache(14, 'omdb_api')
def omdb_api_request(*args, **kwargs):
    """ Request from OMDb API and store in cache for 14 days"""
    request = OMDB_API
    request = request + _omdb_apikey + OMDB_ARG + '&r=xml'
    for key, value in kwargs.items():
        if value:  # Don't add empty kwargs
            request = request + '&' + key + '=' + value
    request = make_request(request, False)
    request = ET.fromstring(request.content)
    request = utils.dictify(request)
    if request and request.get('root') and not request.get('root').get('response') == 'False':
        request = request.get('root').get('movie')[0]
    else:
        request = {}
    return request
