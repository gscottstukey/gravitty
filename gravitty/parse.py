# -*- coding: utf-8 -*-
import pandas as pd
import re

# Source: http://stackoverflow.com/posts/6027703/revisions
def __flatten(d, lkey=''):
    ''' Flattens nested dictionaries. Resulting dictionary has flattened
    keys with underscores concatenating parent & children keys'''
    ret = {}
    for rkey,val in d.items():
        key = lkey + rkey
        if isinstance(val, dict):
            ret.update( __flatten(val, key + '_') )
        else:
            ret[key] = val
    return ret


def __parse_user_tweets(tweets, src='', sub=None, sub_cond=None, cond=None):
    '''
    Parse each user's list of tweet objects. Logic of function is tailored
    to meet the data structure found in tweet dicts.

    tweets: List of tweets
    src: String. Source field where data is located
    sub: String | Int. Sub field or list index to be returned from tweet[
    src] (Optional)
    sub_cond: String. Field in tweet whose value must be equal to cond for
    tweet[src] to be included. (Optional)
    cond: String. If tweet[sub_cond] == cond, d[src] added to returned result.
    return: Set of (filtered) tweet[src] fields
    '''

    if not type(tweets) == list:
        return []

    result = set()

    for tweet in tweets:

        # flatten the tweet structure if src isn't in it. Hopefully it is
        # afterwards!
        d = tweet if src in tweet else __flatten(tweet)

        # Straightforard conditional case
        if sub != None and sub_cond != None and src in d:
            for x in d[src]:
                if d[sub_cond] == cond:
                    result.add(x[sub])

        # Straightforard sub-field case
        elif sub != None and src in d:
            for x in d[src]:
                result.add(x[sub])

        # Last chance for any data to be included...
        elif src in d:

            if sub_cond != None:
                # Sub-condition present & data is a list
                if d[sub_cond] == cond and type(d[src]) == list:
                    for x in d[src]:
                        result.add(x) # add each item

                # Sub-condition present & data is anything else
                elif d[sub_cond] == cond and type(d[src]) != list:
                    result.add(d[src]) # add the whole thing

            else:
                # If we're here, it's because we're looking at hashtags.
                # We treat this slightly different due to unicode & capital
                # letter issues
                if type(d[src]) == list:
                    for x in d[src]:
                        x = ''.join([str(txt).lower()
                                     if ord(txt) < 128 else '' for txt in x])
                        if re.search('[a-z]+', x):
                            result.add(x)

    return result


def __parse_user_info(info, src=''):
    ''' Returns source field from info dictionary '''
    if src in info:
        return info[src]
    return ''


def __parse_user_followers(followers):
    ''' Returns a set of followers from a list '''
    return set(followers)


def __parse_user_following(following):
    ''' Returns a set of friends from a list '''
    return set(following)


def __parse_user_lists(user_list):
    ''' Returns a set of list ids from a list of user_list dictionaries '''
    if not type(user_list) == list: # Some people aren't in any lists.
        return set()
    return set([ul['id'] for ul in user_list])


def parse_dataframe(in_df):
    '''
    Extracts key pieces of data from raw user dataframe.

    in_df: Raw user dataframe from cache/twitter.

    return: Cleaned dataframe ready to have scored for pair-wise user
    similarity
    '''
    df = pd.DataFrame()
    df['id'] = in_df.index
    df = df.set_index('id')

    df['screen_name'] = in_df['info'].apply(__parse_user_info,
                                            src='screen_name')

    df['name'] = in_df['info'].apply(__parse_user_info,
                                     src='name')

    df['location'] = in_df['info'].apply(__parse_user_info,
                                         src='location')

    df['tweets'] = in_df['tweets'].apply(__parse_user_tweets,
                                         src='text',sub_cond='lang',cond='en')

    df['mentions'] = in_df['tweets'].apply(__parse_user_tweets,
                                           src='user_mentions', sub='id')

    df['hashtags'] = in_df['tweets'].apply(__parse_user_tweets,
                                           src='hashtags')

    df['urls'] = in_df['tweets'].apply(__parse_user_tweets,
                                       src='urls', sub=0)

    df['followers'] = in_df['followers'].apply(__parse_user_followers)

    df['following'] = in_df['following'].apply(__parse_user_following)

    df['list'] = in_df['list'].apply(__parse_user_lists)

    return df


def filter_dataframe(in_df, min_followers=1, min_following=1, min_tweets=0):
    '''
    Prunes inactive/noisy users from dataframe.

    in_df: Pandas dataframe. Must contain 'followers', 'following' and
    'tweets' as columns
    min_followers: Integer
    min_following: Integer
    min_tweets: Integer

    return: Pruned dataframe as a copy.
    '''
    df = in_df.copy()
    df = df[df['followers'].apply(len) >= min_followers]
    df = df[df['following'].apply(len) >= min_following]
    df = df[df['tweets'].apply(len) >= min_tweets]
    return df