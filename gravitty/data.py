# -*- coding: utf-8 -*-
import pandas as pd
import twitter
import time

URLS = ('url', 'urls')
FOLLOWERS_CAP = 50000
FOLLOWING_CAP = 50000

API_CALLS = {'list': 'GetListsList',
             'following': 'GetFriendIDs',
             'followers':'GetFollowerIDs',
             'tweets': 'GetUserTimeline',
             'info': 'GetUser',
             }

API_ARGS = {'list': {},
            'following': {},
            'followers': {},
            'tweets': {'count': 200, 'trim_user': True},
            'info': {},
            }


def __traverse(in_dict, lookup):
    '''
    Traverse dictionary looking for keys in the lookup tuple, converting
    values to a list of items.

    Why? Because mongo doesn't like keys with periods in them and twitter
    returns shortened urls and their destinations as key-value pairs.
    '''

    d = in_dict.copy()
    for k, v in d.iteritems():

        if k in lookup and type(v) == dict:
            d[k] = d[k].items()

        elif type(v) == dict:
            d[k] = __traverse(v, lookup)

    return d


def __get_cache(db, followers):
    '''
    Mass collection of cached data. Get all documents from the database that
    have an id in followers.

    db: Mongodb database object.
    followers: List of followers. Each element should be a user id integer.

    return: Nested Dictionary with found/cached user_ids as parent keys.
    Each user_id is mapped to a dictionary of data type - value pairs.
    '''

    result = {}

    curs = db.data.find({'id': {'$in': followers}}, timeout=False)

    for data in curs:

        uid = data['id']

        dtype = data['type']

        if uid not in result:
            result[uid] = {}

        result[uid][dtype] = data['data']

    curs.close()

    return result


def __get_cache_for_user(db, user_id, cache_type):
    '''
    Query database for specific User ID and data type.

    db: Mongo database object
    user_id: Integer
    cache_type: String

    return: Data from cache (No specified type). If not in cache, returns None
    '''

    if user_id:
        tmp = db.data.find_one({'id': user_id, 'type': cache_type})
        if tmp:
            return tmp['data']
    return None


def __make_cache_for_user(db, data, user_id, cache_type):
    ''' Write data for user/type in database. Returns nothing. '''
    db.data.update({'id': user_id, 'type': cache_type},
                   {'$set': {'data': data}},
                   upsert = True)


def get_user_data_by_type(db, api, screen_name=None,
                          user_id=None, data_type=None, force=False):
    '''
    Get data for a specific user, for a specific data type. If force is
    True, data will be pulled from twitter regardless of whether it has
    previously been cached and will replace the cached data.

    db: mongo database object
    api: twitter api object
    screen_name: String, Optional.
    user_id: Integer, Optional if screen_name provided.
    data_type: String. Data type to query for
    force: Boolean. If true will query twitter regardless of whether cache
    exists.

    return: List/Dictionary based on data type selection.
    '''

    data = None if force else __get_cache_for_user(db, user_id, data_type)

    if data == None:
        try:
            # Ugly code. Since python will choke if we pass any api-specific
            # methods (or declare them in a dict at the top of the page),
            # we must resort to building up the function call as a string
            # and evaluating it, otherwise this part of the function would
            # contain a lot of if-else statements.
            data = eval('api.' + API_CALLS[data_type] + \
                        '(screen_name=screen_name, user_id=user_id, ' + \
                        '**API_ARGS[data_type])')

        except twitter.error.TwitterError as e:
            raise e

        if data_type == 'list':
            data = [__traverse(x.AsDict(), URLS) for x in data]

        elif data_type == 'tweets':
            data = [__traverse(x.AsDict(), URLS) for x in data]

        elif data_type == 'info':
            data = __traverse(data.AsDict(), URLS)

        __make_cache_for_user(db, data, user_id, data_type)

    return data


def get_user_data(db, api, name=None, uid=None, ctr=0, force=False):
    '''
    Get all data types for a given user. If user is protected/suspended,
    returns None. If user has too many friends or followers, specified by
    constants FOLLOWERS_CAP and FOLLOWING_CAP, respectively, returns None.
    Without this constraint, rate limits are hit arbitrarily trying to query
    friends/followers at 5k ID's per time (twitter api's limit).

    db: Mongodb database object
    api: Twitter api object
    name: String. Screen name of user
    uid: Integer. User ID.
    ctr: Rate Limit Retry Counter. Do not use.
    force: Boolean. If true will query twitter regardless of whether cache
    exists.

    return: tuple of lists/dictionaries or None
    '''


    try:
        target = get_user_data_by_type(db, api, screen_name=name,
                                       user_id=uid, data_type='info',
                                       force=force)

        if 'followers_count' in target:
            if target['followers_count'] > FOLLOWERS_CAP:
                return None

        if 'friends_count' in target:
            if target['friends_count'] > FOLLOWING_CAP:
                return None

        tweets = get_user_data_by_type(db, api, user_id=target['id'],
                                       data_type='tweets', force=force)

        user_lists = get_user_data_by_type(db, api, user_id=target['id'],
                                           data_type='list', force=force)

        followers = get_user_data_by_type(db, api, user_id=target['id'],
                                          data_type='followers', force=force)

        following = get_user_data_by_type(db, api, user_id=target['id'],
                                          data_type='following', force=force)

        return target, tweets, followers, following, user_lists

    except (twitter.error.TwitterError, twitter.TwitterError) as err:

        if str(err)[0:3] == 'Not' or ctr > 15:
            print 'User is protected:', uid

        elif '63' in str(err):
            print 'User has been suspended:', uid

        elif '88' in str(err):
            print 'Rate Limit reached on:', uid
            time.sleep(60)
            return get_user_data(db, api, name = name, uid = uid, ctr = ctr+1)

        else:
            print err

        return None


def get_follower_data(db, apis, followers, force=False):
    '''
    Get all data for all follower ids passed in followers.

    db: mongodb database object
    apis: list of twitter API objects to be used in a round-robin fashion
    for each download
    followers: list of user ids
    force: Boolean. If true will query twitter regardless of whether cache
    exists.

    return: Pandas Dataframe containing the raw info, tweets, followers,
    following, and list returned from cache/twitter. Dataframe is indexed by
    user_id.
    '''
    num_apis = len(apis)

    num_followers = len(followers)

    # Begin by doing a mass-check for cached data
    if force:
        result = {}
    else:
        result = __get_cache(db, followers)

    for ind, uid in enumerate(followers):

        if uid in result:
            if len(result[uid].keys()) == 5:
                continue
        else:
            result[uid] = {}

        print uid, ind + 1, 'of', num_followers

        n = ind % num_apis

        user_data = get_user_data(db, apis[n], uid=uid, force=force)

        if user_data is not None:
            result[uid]['info'] = user_data[0]
            result[uid]['tweets'] = user_data[1]
            result[uid]['followers'] = user_data[2]
            result[uid]['following'] = user_data[3]
            result[uid]['list'] = user_data[4]
        else:
            del result[uid]

    # Dropna() will not drop fields that are empty, but not blank (e.g.
    # someone who is not a part of any list membership will not be dropped).
    try:
        return pd.DataFrame(result).transpose().dropna()

    except ValueError:
        return pd.DataFrame().from_dict(result, orient='index').dropna()