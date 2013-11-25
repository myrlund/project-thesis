# encoding: utf-8

import sys
import json
import threading
import operator
import re
import sqlite3
import math

from lib import netflix
from lib.datumbox import DatumBox
from lib.twitter import Twitter, Tweet

def load_config(config_file):
    f = open('config.json', 'r')
    config = json.loads(f.read())
    f.close()
    return config

CONFIG = load_config('config.json')

def connect():
    return sqlite3.connect('data.db')
    
def get_cached_tweet_sentiment(tweet_id):
    conn = connect()
    with conn:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS cached_sentiments (tweet_id VARCHAR(50), sentiment VARCHAR(50))")
        cursor.execute("SELECT sentiment FROM cached_sentiments WHERE tweet_id = ?", (tweet_id,))
        rows = cursor.fetchall()
        
        if len(rows) > 0:
            return rows[0][0]
        else:
            return None

def cache_tweet_sentiment(tweet):
    conn = connect()
    with conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO cached_sentiments VALUES (?, ?)", (tweet.id, tweet.sentiment))

def get_tweets(query, result_type='popular'):
    # Search the Twitter API for the given title
    twitter_client = Twitter(CONFIG['twitter'])
    tweet_data = twitter_client.search("\"%s\" -download -stream -#nw -#nowwatching -RT" % (query,), result_type=result_type, count=30)
    
    if DEBUG: print "Retrieved %d tweets (with result type %s)." % (len(tweet_data), result_type)
    
    # if DEBUG:
    #     print json.dumps(tweet_data[0], sort_keys=True, indent=4, separators=(',', ': '))
    
    # Build simple Twitter objects
    tweets = map(Tweet, tweet_data)
    
    # Add a filtered version of the tweet text
    pattern = re.compile(query.replace(" ", " ?"), re.I)
    for tweet in tweets:
        tweet.sentiment = get_cached_tweet_sentiment(tweet.id)
        tweet.filtered_text = pattern.sub('', tweet.text)
    
    return tweets

def apply_sentiment(datumbox, tweet):
    encoded_tweet = tweet.filtered_text.encode('utf8')
    try:
        tweet.sentiment = datumbox.twitter_sentiment_analysis(encoded_tweet)
    except Exception as e:
        print "This query spawned 500 error: %s" % encoded_tweet
        print e

def batches(l, n):
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

def get_sentiments(tweets):
    # Sentiment analyze tweets
    if DEBUG: print "Starting sentiment analysis."
    datumbox = DatumBox(CONFIG['datumbox']['API_KEY'])
    
    for batch in batches(tweets, CONFIG['datumbox']['BATCH_SIZE']):
        threads = [threading.Thread(target=apply_sentiment, args=(datumbox, tweet,)) for tweet in batch if tweet.sentiment is None]
        [thread.start() for thread in threads]
        [thread.join() for thread in threads]
        if DEBUG:
            for tweet in batch:
                print unicode(tweet)
    
    for tweet in tweets:
        cache_tweet_sentiment(tweet)
    
    sentiments = [tweet.sentiment for tweet in tweets]
    return sentiments

def weigh_sentiments(sentiments):
    # Filter out missing sentiment values
    not_none = lambda sentiment: sentiment is not None
    valid_sentiments = filter(not_none, sentiments)
    
    # Apply some weights to quantify result vector
    if DEBUG: print "Applying weights."
    
    weights = {
        'positive': 5,
        'negative': 1,
        'neutral': 3,
    }
    apply_weight = lambda sentiment: weights[sentiment]
    weights = map(apply_weight, valid_sentiments)
    
    if DEBUG: print "Result vector: (%s)" % ", ".join(["%d" % weight for weight in weights])
    
    return tuple(weights)

def generate_ratings(title, source_type='popular'):
    tweets = get_tweets(title, result_type=source_type)
    sentiments = get_sentiments(tweets)
    weights = weigh_sentiments(sentiments)
    return weights

def average(s):
    return sum(s) / float(len(s))

def variance(s):
    mean = average(s)
    return average(map(lambda x: (x - mean)**2, s))

def stddev(s):
    return math.sqrt(variance(s))

def analyze_ratings(ratings):
    mean = average(ratings)
    var = variance(ratings)
    return mean, var

def title_score(title, heuristic='popular'):
    ratings = generate_ratings(title, source_type=heuristic)
    return analyze_ratings(ratings)

def nf_title_score(title):
    ratings = netflix.ratings_for_movie_title(title)
    return analyze_ratings(ratings)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Parses sentences.")
    parser.add_argument('-t', nargs=1, help="type of search", choices=('recent', 'popular', 'mixed'), default=['popular'])
    parser.add_argument('--debug', action='store_true', help="print traces and parse trees")
    # parser.add_argument('titles', nargs='+', help="Item titles to analyze.")

    args = parser.parse_args()
    
    DEBUG = args.debug
    
    titles = [
        "pulp fiction",
        "the shining",
        "mission: impossible",
        "the matrix",
        "the godfather",
        "forrest gump",
        "the pianist",
        "citizen kane",
        "a clockwork orange",
        "Requiem for a Dream",
    ]
    
    tw_means = []
    nf_means = []
    for title in titles:
        print title
        tw_score = title_score(title, heuristic=args.t[0])
        tw_means.append(tw_score[0])
        nf_score = nf_title_score(title)
        nf_means.append(nf_score[0])
        print "Scoring %s." % title
        print "Twitter mean/variance: %.2f/%.2f" % tw_score
        print "Netflix mean/variance: %.2f/%.2f" % nf_score
    
    tw_avg = average(tw_score)
    nf_avg = average(nf_score)
    
    a = map(lambda x: x - tw_avg, tw_means)
    b = map(lambda x: x - nf_avg, nf_means)
    
    a2 = sum(map(lambda x: x ** 2, a))
    b2 = sum(map(lambda x: x ** 2, b))
    
    cov = sum(map(lambda ab: ab[0] * ab[1], zip(a, b)))
    
    # tw_stddev = math.sqrt(variance(tw_score))
    # nf_stddev = math.sqrt(variance(nf_score))
    
    correlation = cov / math.sqrt(a2 * b2)
    
    print
    print "Twitter stddev: %.2f" % sum(a)
    print "Netflix stddev: %.2f" % sum(b)
    print "Covariance:  %.2f" % cov
    print "Correlation: %.2f" % correlation
