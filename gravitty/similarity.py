# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd

FOLLOWING_EACH_OTHER_WEIGHT = 10.
FOLLOWING_ONE_WAY_WEIGHT = 5.

SHARED_FOLLOWERS_WEIGHT = 1.
SHARED_FOLLOWING_WEIGHT = 1.

SHARED_LIST_WEIGHT = 1.
SHARED_MENTION_WEIGHT = 1.
SHARED_HASHTAG_WEIGHT = 1.
SHARED_URLS_WEIGHT = 1.

MENTION_OTHER_USER_WEIGHT = 10.


def compute_similarity(user1_id, user1, user2_id, user2):
    '''
    Given the user ids and corresponding rows of data for two users, find a
    weighted attraction score based on direct relationship metrics (e.g.
    following each other, mentioning each other, etc.) as well as one step
    removed latent factors, such as shared followers/friends, shared list
    membership, shared references to hashtags, and shared mentions.

    In essence this performs a weighted one-mode projection, treating
    followers, friends, mentions, etc. as separate graph classes and projecting
    common interests onto an undirected relationship between these two users.

    The algorithm uses adjustable weights (see constants set above) to weigh
    the relative importance of each type of common interest / relationship.
    The default levels were set by my intuition without any empirical
    evidence and can (should?) be adjusted.

    This algorithm is naive in the sense that it does not correct for
    common interests that have little information gain (e.g. two
    users mentioning a mutual friend is more indicative of a close
    relationship than mentioning @barackobama). Such a calculation would
    require additional information (e.g. how many other people are
    referencing @barackobama, not just in my set of users), which would
    require a prohibitive number of api calls to ascertain.

    user1_id: Integer
    user1: Pandas Dataframe/Series containing user1's information.
    user2_id: Integer
    user2: Pandas Dataframe/Series containing user2's information.

    return: Similarity score as a float
    '''


    user1_follow_user2 = user2_id in user1['following']
    user2_follow_user1 = user2_id in user1['followers']

    user1_mention_user2 = user2_id in user1['mentions']
    user2_mention_user1 = user1_id in user2['mentions']

    shared_followers = user1['followers'].intersection(user2['followers'])
    shared_following = user1['following'].intersection(user2['following'])

    shared_list = user1['list'].intersection(user2['list'])
    shared_hashtags = user1['hashtags'].intersection(user2['hashtags'])
    shared_mentions = user1['mentions'].intersection(user2['mentions'])
    shared_urls = user1['urls'].intersection(user2['urls'])

    similarity  = FOLLOWING_EACH_OTHER_WEIGHT * \
                  (user1_follow_user2 and user1_follow_user2)
    similarity += FOLLOWING_ONE_WAY_WEIGHT * \
                  (user1_follow_user2 ^ user2_follow_user1)
    similarity += MENTION_OTHER_USER_WEIGHT * user1_mention_user2
    similarity += MENTION_OTHER_USER_WEIGHT * user2_mention_user1
    similarity += SHARED_FOLLOWERS_WEIGHT * len(shared_followers)
    similarity += SHARED_FOLLOWING_WEIGHT * (len(shared_following) - 1)
    similarity += SHARED_LIST_WEIGHT * len(shared_list)
    similarity += SHARED_MENTION_WEIGHT * len(shared_mentions)
    similarity += SHARED_HASHTAG_WEIGHT * len(shared_hashtags)
    similarity += SHARED_URLS_WEIGHT * len(shared_urls)

    return similarity


def make_similarity_dataframe(df):
    '''
    Performs a pair-wise latent similarity calculation on every pair of users
    in the provided user dataframe. Produces a dataframe instead of a numpy
    matrix for easier indexing by downstream functions.

    See compute_similarity for additional details on how this score is
    computed.

    df: Pandas Dataframe. Should contain the parsed data produced from
    parse_dataframe().

    return: Pandas Dataframe indexed & columned by user_id. Similarity
    scores are undirected.
    '''

    similarity_df = pd.DataFrame(data=np.zeros([df.shape[0]]*2),
                                 index=df.index, columns=df.index)

    for i, user1_id in enumerate(df.index[:-1]):

        for user2_id in df.index[i+1:]:

            similarity = compute_similarity(user1_id, df.ix[user1_id, :],
                                            user2_id, df.ix[user2_id, :])

            similarity_df.ix[user1_id, user2_id] = similarity
            similarity_df.ix[user2_id, user1_id] = similarity

    return similarity_df
