import xbmc
import json
import apis
from datetime import datetime
from copy import copy
from globals import _addonlogname, _url
from urllib import urlencode


def jsonrpc_library(method="VideoLibrary.GetMovies", dbtype="movie"):
    query = {"jsonrpc": "2.0",
             "params": {"properties": ["title", "imdbnumber"]},
             "method": method,
             "id": 1}
    response = json.loads(xbmc.executeJSONRPC(json.dumps(query)))
    my_dict = {}
    dbid_name = '{0}id'.format(dbtype)
    key_to_get = '{0}s'.format(dbtype)
    for item in response.get('result', {}).get(key_to_get, []):
        my_dict[item.get('title')] = {'imdb_id': item.get('imdbnumber'), 'dbid': item.get(dbid_name)}
    # kodi_log(my_dict, 1)
    return my_dict


def get_url(**kwargs):
    return '{0}?{1}'.format(_url, urlencode(kwargs))


def age_difference(birthday, deathday=''):
    try:  # Added Error Checking as strptime doesn't work correctly on LibreElec
        deathday = datetime.strptime(deathday, '%Y-%m-%d') if deathday else datetime.now()
        birthday = datetime.strptime(birthday, '%Y-%m-%d')
        age = deathday.year - birthday.year
        if birthday.month * 100 + birthday.day > deathday.month * 100 + deathday.day:
            age = age - 1
        return age
    except Exception:
        return


def kodi_log(value, level=0):
    if level == 1:
        xbmc.log('{0}{1}'.format(_addonlogname, value), level=xbmc.LOGNOTICE)
    else:
        xbmc.log('{0}{1}'.format(_addonlogname, value), level=xbmc.LOGDEBUG)


def dictify(r, root=True):
    if root:
        return {r.tag: dictify(r, False)}
    d = copy(r.attrib)
    if r.text:
        d["_text"] = r.text
    for x in r.findall("./*"):
        if x.tag not in d:
            d[x.tag] = []
        d[x.tag].append(dictify(x, False))
    return d


def del_dict_keys(dictionary, keys):
    for key in keys:
        if dictionary.get(key):
            del dictionary[key]
    return dictionary


def concatinate_names(items, key, separator):
    concat = ''
    for i in items:
        if i.get(key):
            if concat:
                concat = '{0} {1} {2}'.format(concat, separator, i.get(key))
            else:
                concat = i.get(key)
    return concat


def dict_to_list(items, key):
    mylist = []
    for i in items:
        if i.get(key):
            mylist.append(i.get(key))
    return mylist


def split_items(items, separator='/'):
    separator = ' {0} '.format(separator)
    if separator in items:
        items = items.split(separator)
    items = [items] if isinstance(items, str) else items  # Make sure we return a list to prevent a string being iterated over characters
    return items


def translate_lookup_ids(items, request, lookup_dict=False, separator='%2C'):
    if items:
        items = split_items(items)
        temp_list = ''
        for item in items:
            query = None
            item_id = None
            if request:  # If we don't have TMDb IDs then look them up
                if lookup_dict:  # Check if we should be looking up in a stored dict
                    if request.get(item):
                        item_id = str(request.get(item))
                else:  # Otherwise lookup IDs via a TMDb search request
                    query = apis.tmdb_api_request_longcache(request, query=item)
                    if query:
                        if query.get('results') and query.get('results')[0]:
                            item_id = query.get('results')[0].get('id')
            else:  # Otherwise we assume that each item is a TMDb ID
                item_id = item
            if item_id:
                if separator:  # If we've got a url separator then concatinate the list with it
                    temp_list = '{0}{1}{2}'.format(temp_list, separator, item_id) if temp_list else item_id
                else:  # If no separator, assume that we just want to use the first found ID
                    temp_list = str(item_id)
                    break  # Stop once we have a item
        if temp_list:
            return temp_list


def iter_props(items, property, itemprops, **kwargs):
    x = 0
    for i in items:
        x = x + 1
        for key, value in kwargs.items():
            if i.get(value):
                itemprops['{0}.{1}.{2}'.format(property, x, key)] = i.get(value)
    return itemprops


def convert_to_plural_type(tmdb_type):
    if tmdb_type == 'tv':
        return 'Tv Shows'
    elif tmdb_type == 'person':
        return 'People'
    else:
        return '{0}s'.format(tmdb_type.capitalize())


def convert_to_kodi_type(tmdb_type):
    if tmdb_type == 'tv':
        return 'tvshow'
    elif tmdb_type == 'person':
        return 'actor'
    else:
        return tmdb_type


def convert_to_library_type(tmdb_type):
    if tmdb_type == 'tv' or tmdb_type == 'movie' or tmdb_type == 'episode' or tmdb_type == 'season':
        return 'video'
    elif tmdb_type == 'image':
        return 'pictures'
    else:
        return ''


def merge_two_dicts(x, y):
    z = x.copy()   # start with x's keys and values
    z.update(y)    # modifies z with y's keys and values & returns None
    return z


def make_kwparams(params):
    tempparams = params.copy()
    return del_dict_keys(tempparams, ['info', 'type', 'tmdb_id', 'filter_key', 'filter_value', 'with_separator', 'with_id'])