# -*- coding: utf-8 -*-
from copy import deepcopy
from data import get_user_data_by_type
import twitter

def convert_id_to_sn(user_id, df, db, api):
    '''
    Efficiently converts a user id to a screen name.

    user_id: Int
    df: Pandas Dataframe. Index should be user_ids and should contain
    'screen_name' as a column. It is fine if user_id is not in the dataframe.
    db: MongoDB database object.
    api: Single twitter API call object.
    return: Screen Name of user id (str). Produces None if user is protected or
    suspended.
    '''

    if user_id in df.index:
        return df.ix[user_id, 'screen_name']

    try:
        info = get_user_data_by_type(db, api,
                                     user_id = user_id,
                                     data_type='info')

    except twitter.error.TwitterError:
        return None

    return info['screen_name']


def get_screen_names(data_in, target, df, db, api):
    '''
    For the given target field in data_in, converts user ids to screen
    names. Given the nested nature of the data object,
    the entirety of the data object is returned for simplicity.

    data_in: Nested Dictionary. Should be a data object produced from
    get_community_analytics
    target: String. Must be a nested field in data object (level ->
    community -> target)
    df: Pandas Dataframe. Index should be user_ids and should contain
    'screen_name' as a column. It is fine if user_id is not in the dataframe.
    db: MongoDB database object.
    api: Single twitter API call object.

    return: Nested Dictionary
    '''
    d = deepcopy(data_in)

    for lvl in d:

        for cid in d[lvl]:

            for i, tag in enumerate(d[lvl][cid][target]):

                sn = convert_id_to_sn(tag, df, db, api)

                if sn == None:
                    d[lvl][cid][target][i] = '@<Protected_User>'

                else:
                    d[lvl][cid][target][i] = '@' + sn

    return d
