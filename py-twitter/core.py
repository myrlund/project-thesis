# encoding: utf-8

import sys
import json
import threading
import operator
import re

from lib.datumbox import DatumBox
from lib.twitter import Twitter, Tweet

CONFIG = json.loads(open('config.json', 'r').read())

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
        threads = [threading.Thread(target=apply_sentiment, args=(datumbox, tweet,)) for tweet in batch]
        [thread.start() for thread in threads]
        [thread.join() for thread in threads]
        if DEBUG:
            for tweet in batch:
                print unicode(tweet)
    
    sentiments = [tweet.sentiment for tweet in tweets]
    return sentiments

def weigh_sentiments(sentiments):
    # Filter out missing sentiment values
    not_none = lambda sentiment: sentiment is not None
    valid_sentiments = filter(not_none, sentiments)
    
    # Apply some weights to quantify result vector
    if DEBUG: print "Applying weights."
    
    weights = {
        'positive': 10,
        'negative': -10,
        'neutral': 2,
    }
    apply_weight = lambda sentiment: weights[sentiment]
    weights = map(apply_weight, valid_sentiments)
    
    if DEBUG: print "Result vector: (%s)" % ", ".join(["%d" % weight for weight in weights])
    
    return tuple(weights)

def analyze_title(title, source_type='popular'):
    tweets = get_tweets(title, result_type=source_type)
    sentiments = get_sentiments(tweets)
    weights = weigh_sentiments(sentiments)
    return weights

def calculate_score(result):
    return sum(result) / float(len(result))

def average(s): return sum(s) * 1.0 / len(s)

def title_score(title, heuristic='popular'):
    result = analyze_title(title, source_type=heuristic)
    score = calculate_score(result)
    print "VARIANCE: %.2f" % average(map(lambda x: (x - score)**2, result))
    return score

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Parses sentences.")
    parser.add_argument('-t', nargs=1, help="type of search", choices=('recent', 'popular', 'mixed'), default=['popular'])
    parser.add_argument('--debug', action='store_true', help="print traces and parse trees")
    parser.add_argument('titles', nargs='+', help="Item titles to analyze.")

    args = parser.parse_args()
    
    DEBUG = args.debug
    
    for title in args.titles:
        print title
        print "Scoring %s." % title
        print "SCORE: %.2f" % title_score(title, heuristic=args.t[0])
