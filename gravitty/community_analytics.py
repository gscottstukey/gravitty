# -*- coding: utf-8 -*-
import graphlab as gl
import networkx as nx
import numpy as np
from community import modularity, partition_at_level
import happy
import d3py

def __extract_tweets(df):
    '''
    df: Pandas dataframe. Must contain 'tweets' column

    return: Flattened list of lower-case, unicode-safe tweets
    '''

    twts = df['tweets'].apply(list).tolist()

    twts = [''.join([str(ltr) if ord(ltr) < 128 else '' for ltr in t.strip()])
            for twt in twts for t in twt]

    return twts


def get_topics(df, stops=set(), tweets=None, num=5):
    '''
    Find latent topics from tweets in dataframe.

    df: Pandas dataframe. Must contain 'tweets' column. (Optional if tweets)
    stops: Set including stop words to be removed during tokenization.
    tweets: List of tweets (str). (Optional if df)
    num: Integer. Number of topics to return.

    return: List of (word, score) tuples from LDA topic model.
    '''

    if tweets == None:
        tweets = __extract_tweets(df)

    tweets = gl.SArray(data=tweets, dtype=str)

    # Graphlab utilizes a list of dicts where the tokenized words are keys
    # and their values are their counts in each doc. count_words()
    # accomplishes this and dict_trim_by_keys removes stop words.
    tweets = tweets.count_words().dict_trim_by_keys(keys=stops)

    model = gl.text.topic_model.create(dataset = tweets, num_topics = num)

    topics = model.get_topics(range(num))

    topics = topics.apply(lambda x: x.values()).astype(list)

    result = {}
    for i in range(num):
        result[i] = [(x[2], x[1]) for x in topics if x[0] == i]

    return result


def get_hashtags(df, num=5):
    '''
    Finds the most frequently used hashtags.

    df: Pandas dataframe. Must contain 'hashtags' column.
    num: Integer. Limits the number of most frequently used hashtags.

    return: List of lower-cased hashtags (does not prefix #).
    '''

    hashtags = reduce(lambda x, y: x + y, df['hashtags'].apply(list).tolist())

    hashtags = sorted([(hashtags.count(x), '#' + x) for x in set(hashtags)],
                      reverse=True)

    return [x[1] for x in hashtags[:num]]


def get_mentions(df, num=5):
    '''
    Find the most frequently mentioned user ids

    df: Pandas dataframe. Must contain 'mentions' column
    num: Integer. Limits the number of most frequently mentioned users

    return: List of most frequently mentioned user ids as integers
    '''

    mentions = reduce(lambda x, y: x + y, df['mentions'].apply(list).tolist())

    mentions = sorted([(mentions.count(x), x) for x in set(mentions)],
                      reverse=True)

    return [x[1] for x in mentions[:num]]


def get_density(subgraph):
    '''
    subgraph: Networkx Graph object

    return: Density of graph
    '''

    return nx.density(subgraph)


def get_most_connected(subgraph, num=5):
    '''
    Find the most influential nodes using the NetworkX's pagerank algorithm.

    subgraph: Networkx Graph object
    num: Limit number of most influential nodes returned

    return: Node IDs of most influential nodes. Returns None if pagerank
    fails to converge.
    '''

    try:
        pr = nx.pagerank(subgraph)

    except nx.exception.NetworkXError:
        return None

    pr = sorted([(val, user) for user, val in pr.iteritems()], reverse=True)

    return [x[1] for x in pr[:num]]


def get_sentiment(df, tweets=None):
    '''
    Find the (very simple) sentiment of a group of tweets using word score.
    Closer to 1 means sad and closer to 9 means happy. Around 5.5 indicates
    neutral.

    df: Pandas dataframe. Must contain 'tweets' column. (Optional if tweets)
    tweets: List of tweets (str). (Optional if df).

    return: Tuple of (mean, standard dev) of scores.
    '''

    if tweets == None:
        tweets = __extract_tweets(df)

    sentiments = happy.hi(tweets)

    return np.mean(sentiments), np.std(sentiments)


def get_community_analytics(df, graph, num_levels, detail=3,
                            community_modularity=None):
    '''
    Returns various trends, topics, statistics, and sentiment for each
    community.

    df: Pandas Dataframe. Must contain tweets, mentions, and hashtags as
    column names.
    graph: Networkx graph object.
    num_levels: Number of levels returned from community detection dendrogram
    detail: Number of items (topics, hashtags, mentions, etc.) to be returned.
    community_modularity: Dictionary of int(community level): float(
    modularity) as a key,value pair. Optional.

    return: Returns a nested dictionary with community level (int) as the
    first level, community id (int) as the second level, and the community
    statistics/information as the third level.
    '''

    stops = gl.text.util.stopwords(lang='en')

    # extra stop words, mostly for rt, url links, unicode, and compound words.
    stops.update(['rt', 'http', 'https', 'ly', 'amp', 'don', 'wasn', 're',
                  'aren', 'didn', 'how', 'nt', 'co', 've', 'gt', 'll',
                  'bit'])

    # get rid of arbitrary single numbers
    stops.update(map(str, range(11)))


    data = {x:{} for x in range(num_levels)}

    for lvl in xrange(num_levels):

        col_name = 'cid' + str(lvl)

        num_of_communities = max(df[col_name])

        for cid in xrange(num_of_communities + 1): # +1 for inclusive rng

            if cid not in data[lvl]:
                data[lvl][cid] = {}

            subdf = df[df[col_name] == cid]

            subgraph = graph.subgraph(subdf.index.tolist())

            tweets = __extract_tweets(subdf)

            data[lvl][cid]['comm_size'] = subdf.shape[0]

            data[lvl][cid]['topics'] = get_topics(subdf, stops,
                                                  tweets=tweets, num=detail)

            data[lvl][cid]['hashtags'] = get_hashtags(subdf, num=detail)

            data[lvl][cid]['mentioned'] = get_mentions(subdf, num=detail)

            data[lvl][cid]['most_connected'] = get_most_connected(subgraph,
                                                                  num=detail)

            data[lvl][cid]['density'] = get_density(subgraph)

            data[lvl][cid]['sentiment'] = get_sentiment(subdf, tweets)

            if community_modularity != None:
                data[lvl][cid]['modularity'] = community_modularity[lvl]
            else:
                data[lvl][cid]['modularity'] = None

    return data


def get_community_assignment(in_df, graph, dendrogram):
    '''
    Utilize dendrogram to find community clusterings at every level
    available. For each hierarchy level, a new column is added to the
    returned df with the community clustering. (e.g. cid0 -> 0,0,1,2,3)

    in_df: Dataframe. Must be indexed by user_id.
    graph: Networkx Graph. Node IDs should match user_ids in dataframe
    dendrogram: List of dictionaries, each dictionary mapping user_id to
    community_id. Each dictionary should represent a level of the clustering
    hierarchy.

    return: Tuple of Dataframe with community id assignment columns added
    and dictionary mapping each level to community modularity (float)
    '''
    df = in_df.copy()

    community_modularity = {}

    for i in range(len(dendrogram)):

        partition = partition_at_level(dendrogram, i)

        # Infrequently, the community detection algorithm will exclude (?) a
        # a user ID or two. Still investgating why. For now, these will be
        # placed into partition 0.
        df['cid' + str(i)] = [partition[ind] if ind in partition else 0
                              for ind in df.index]

        community_modularity[i] = modularity(partition, graph)

    return df, community_modularity


def create_community_graph(data, dendrogram):
    '''
    Creates an undirected, unweighted Networkx graph where each node
    represents detected communities. Data from community analytics function is
    appended to nodes as attributes.

    data: Nested dictionary returned from community_analytics function
    dendrogram: List of dictionaries, each dictionary mapping user_id to
    community_id. Each dictionary should represent a level of the clustering
    hierarchy.

    return: NetworkX Graph object
    '''
    g = nx.DiGraph()

    for i in data:

        dmap = None if i + 1 >= len(dendrogram) else dendrogram[i + 1]

        for j in data[i]:

            child_node = str(i) + '-' + str(j)
            g.add_node(child_node, attr_dict=data[i][j])

            g.node[child_node]['name'] = child_node
            g.node[child_node]['group'] = i

            if dmap != None:
                parent_node = str(i+1) +'-'+ str(dmap[j])
                g.add_edge(child_node, parent_node)
                g.edge[child_node][parent_node]['value'] = 1

    return g


def create_community_json(graph, user_info):
    '''
    Creates a json representation for a given graph. Intended to be used
    with d3.js for visual represenation of community graph.

    Utilizes d3py library (a requirement for this library) to create JSON
    object. d3py reference material be found here:
    https://github.com/mikedewar/d3py

    graph: NetworkX object. Does not need to necessary follow a particular
    structure, but function is intended for use with graphs created by
    create_community_graph function.

    user_info: Dictionary containing target user details. Should contain all
    items found by converting a twitter user status object to a dictonary.

    return: dictionary/json containing all data from graph in node elements
    and all information from user_info in key named 'root'.
    '''

    community_json = d3py.json_graph.node_link_data(graph)

    # Add user information info to the json file
    community_json['root'] = {}
    community_json['root']['id_'] = user_info['id']
    community_json['root']['screen_name'] = user_info['screen_name']
    community_json['root']['name_'] = user_info['name']
    community_json['root']['description'] = user_info['description']
    community_json['root']['friends_count'] = user_info['friends_count']
    community_json['root']['followers_count'] = user_info['followers_count']

    return community_json