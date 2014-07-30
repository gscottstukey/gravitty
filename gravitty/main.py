# -*- coding: utf-8 -*-
import pymongo, pickle, os
from utils import oauth_login
from data import get_user_data, get_follower_data
from parse import filter_dataframe, parse_dataframe
from similarity import make_similarity_dataframe
from graph import make_graph
from community import generate_dendrogram
from community_analytics import (get_community_assignment,
                                 get_community_analytics,
                                 create_community_graph,
                                 create_community_json)
from conversions import get_screen_names

API_PATH = 'api_keys/'
PKL_PATH = 'cache/'
PKL_FILE_EXT = 'pkl'
DBG_FILE_EXIT = 'pkl_debug'
DB_NAME = 'twitter'

def load(screen_name=None, user_id=None, force_db_update = False,
                  force_twitter_update=False, debug=False):
    '''
    Main entry point into gravitty module. Should be used by importing
    gravitty and calling gravitty.load('<your_screen_name').

    Please see the readme at github.com/ericjeske/gravitty for mandatory setup
    instructions and api requirements.

    The load function will make every attempt to load data from cache
    sources (mongoDB) before using twitter's api. It is, however, suggested
    that multiple twitter api keys are utilized with this app to avoid rate
    limiting restrictions.

    By default, running this function will return a json object that can
    be parsed by d3.js to create a community graph. Additional information,
    including the raw twitter data, parsed twitter data, user similarity,
    community clustering dendrogram, community analytics data, community
    networkx graph, and community json object, can be returned by passing in
    debug=True.

    Also, by default, this app will create two pickled objects,
    one containing the debug data described above, the other containing the
    community json file. Subsequent calls for the same user will use this
    data to save time (and api calls).

    To override the use of pickled data, use force_db_update = True. Data
    for each follower will be pulled from mongoDB if possible, otherwise it
    will be pulled from twitter.

    To do a clean-slate download, downloading everything from twitter,
    use force_twitter_update = True.

    '''

    if screen_name == None and user_id == None:
        raise Exception('Please enter an id or name')

    # Assume that if screen_name was not provided (only user id) then a
    # pickle has not been created.
    if screen_name is not None:
        ABS_PKL_PATH = os.path.join(os.path.dirname(__file__), PKL_PATH)
        sn_file = ABS_PKL_PATH + str(screen_name) + '.' + PKL_FILE_EXT
        sn_file_debug = ABS_PKL_PATH + str(screen_name) + '.' + DBG_FILE_EXIT

        # Check to see if there are pickles for the user. Note that this will
        # be overriden if force_db_update is set to true
        if os.path.isfile(sn_file_debug) and debug \
                and not force_twitter_update and not force_db_update:
            return pickle.load(open(sn_file_debug, 'rb'))

        if os.path.isfile(sn_file) \
                and not force_twitter_update and not force_db_update:
            return pickle.load(open(sn_file, 'rb'))

    # Use api credentials from files located in the API_PATH.
    ABS_API_PATH = os.path.join(os.path.dirname(__file__), API_PATH)
    apis = oauth_login(ABS_API_PATH)

    # Try to start up a mongo database connection to cache data in
    try:
        conn = pymongo.MongoClient("localhost", 27017)

    except pymongo.errors.ConnectionFailure:
        print 'Please run mongod and re-run program'
        raise Exception('DBError')

    db = conn[DB_NAME]

    # Get the target user's data from either the screen_name or user_id
    user_data = get_user_data(db, apis[0],
                              name = screen_name, uid = user_id,
                              force = force_twitter_update)

    # If the user is protected (or has more than the maximum
    # followers/friends), then return an error
    if user_data == None:
        print 'Was unable to access data for %s / %s' % (screen_name, user_id)
        raise Exception('TargetError')

    user_info, user_tweets, followers, following, user_lists = user_data

    # Using the target user's list of followers (user ids), get the same
    # information we just got for the target user for each of its followers
    raw_df = get_follower_data(db, apis, followers,
                               force = force_twitter_update)

    # Filter the dataframe for inactive users. Then parse the raw dataframe
    # to extract the relevant features from the raw data
    df = parse_dataframe( filter_dataframe(raw_df) )

    # With the features in hand, calculate the latent similarity between each
    # set of users. See similarity.py for more detail on the calculations of
    # this similarity metric.

    # The resulting dataframe will be a square matrix indexed/columned by
    # user_id and contain the undirected edge weights between each pair of
    # users.
    df_similarity = make_similarity_dataframe(df)

    # Make an undirected representing the relationship between each user,
    # if any. Each node ID is the user ID, each edge weight is equal to the
    # similarity score between those two users.
    graph = make_graph(df, df_similarity)

    # Using the louvain method, find communities within the weighted graph.
    # The returned dendrogram is a list of dictionaries where the values of
    # each dictionary are the keys of the next dictionary. The length of the
    # dendrogram indicates the number of levels of community clusters
    # detected.
    dendrogram = generate_dendrogram(graph)

    # Add a final mapping to the dendrogram that maps everyone into the
    # same community. They are, after all, followers of the same user.
    dendrogram.append({k:0 for k in dendrogram[-1].values()})

    # Modify the dataframe to contain columns titled 'cid + <level>'. Each
    # column contains the community id's for that level for each user.
    # Also, this is a convenient time to calculate graph modularity at each
    # level so produce that here as well.
    df, modularity = get_community_assignment(df, graph, dendrogram)

    num_levels = len(dendrogram)

    # For each community at each level of the dendrogram, find the topics,
    # sentiment, biggest influencers, etc. for each.
    data = get_community_analytics(df, graph, num_levels,
                                   community_modularity = modularity)

    # Both the mentioned and most connected users fields from the community
    # analytics function are user ids. Turn them into screen names.
    data = get_screen_names(data, 'mentioned', df, db, apis[0])
    data = get_screen_names(data, 'most_connected', df, db, apis[0])

    # Close the database connection. It is no longer needed.
    conn.close()

    # Create a networkx graph where each node represents a community. Edges
    # represent membership into larger communities at the next level up (
    # down?) the dendrogram and have no edge weights. The data obtained in
    # the previous steps from community_analytics is loaded into the
    # attributes of each node.
    community_graph = create_community_graph(data, dendrogram)

    # Parse this graph into a json representation for use & consumption by
    # d3.js
    community_json = create_community_json(community_graph, user_info)

    # Just in case we don't have the screen name, grab it.
    if screen_name is None:
        screen_name = user_info['screen_name']

    # Pickle the objects for reuse.
    ABS_PKL_PATH = os.path.join(os.path.dirname(__file__), PKL_PATH)
    sn_file = ABS_PKL_PATH + str(screen_name) + '.' + PKL_FILE_EXT
    sn_file_debug = ABS_PKL_PATH + str(screen_name) + '.' + DBG_FILE_EXIT

    pickle.dump((raw_df, df, df_similarity, dendrogram, data,
                 community_graph, community_json), open(sn_file_debug, 'wb'))

    pickle.dump(community_json, open(sn_file, 'wb'))

    # If debug is true, return all of the precusor objects along with the json
    if debug:
        return (raw_df, df, df_similarity, dendrogram, data,
                community_graph, community_json)

    # Otherwise return the json object
    return community_json


def available():
    '''
    Find all users that have been previously analyzed and whose community
    graphs are available for display. All other requests to load() will
    require processing.

    return: List of all users' screen names if a non-debug pickled object
    is found in the cache directory.
    '''

    ABS_PKL_PATH = os.path.join(os.path.dirname(__file__), PKL_PATH)

    files_exts = [f.split('.') for f in os.listdir(ABS_PKL_PATH)
                  if os.path.isfile(os.path.join(ABS_PKL_PATH,f))
                     and f[0] != '.']

    return [f[0] for f in files_exts if f[1] == PKL_FILE_EXT]