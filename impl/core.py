# encoding: utf-8

import sys
import threading
import operator
import re
import sqlite3
import math

from lib import netflix
from lib.datumbox import DatumBox
from lib.twitter import Twitter, Tweet, NotEnoughTweetsError

from utils import *
from plots import barplot

CONFIG = load_config('config.json')

def get_tweets(query, result_type='popular'):
    # Search the Twitter API for the given title
    twitter_client = Twitter(CONFIG['twitter'])
    tweet_data = twitter_client.search("\"%s\" -download -stream -#nw -#nowwatching -RT" % (query,), result_type=result_type, count=50)
    
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
        'negative': 1,
        'neutral': 3,
        'positive': 5,
    }
    apply_weight = lambda sentiment: weights[sentiment]
    weights = map(apply_weight, valid_sentiments)
    
    if DEBUG: print "Result vector: (%s)" % ", ".join(["%d" % weight for weight in weights])
    
    return tuple(weights)

def generate_ratings(title, source_type='popular', threshold=5):
    tweets = get_tweets(title, result_type=source_type)
    if len(tweets) < threshold:
        raise NotEnoughTweetsError("Number of tweets below threshold of %d." % threshold)
    
    sentiments = get_sentiments(tweets)
    weights = weigh_sentiments(sentiments)
    return weights

def analyze_ratings(ratings):
    mean = average(ratings)
    var = stddev(ratings)
    return mean, var

def title_score(title, heuristic='popular', threshold=5):
    ratings = generate_ratings(title, source_type=heuristic, threshold=threshold)
    return analyze_ratings(ratings)

def nf_title_score(title):
    ratings = netflix.ratings_for_movie_title(title)
    return analyze_ratings(ratings)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Parses sentences.")
    parser.add_argument('-t', help="type of search", choices=('recent', 'popular', 'mixed'), default='popular')
    parser.add_argument('--threshold', help="type of search", type=int, default=5)
    parser.add_argument('--normalize', action='store_true', help="normalize twitter ratings to match average mean of netflix data")
    parser.add_argument('--top-movies-only', action='store_true', help="only load top movies")
    parser.add_argument('--plot', action='store_true', help="plot the results and show them")
    parser.add_argument('--show-errors', action='store_true', help="plot the standard deviations and other errors")
    parser.add_argument('--debug', action='store_true', help="print traces and parse trees")
    # parser.add_argument('titles', nargs='+', help="Item titles to analyze.")

    args = parser.parse_args()
    
    DEBUG = args.debug
    
    # titles = [
    #     "Pulp Fiction",
    #     "The Shining",
    #     "Mission: Impossible",
    #     "The Matrix",
    #     "The Godfather",
    #     "Forrest Gump",
    #     "A Clockwork Orange",
    # ]
    
    tw_means = []
    tw_stddevs = []
    nf_means = []
    nf_stddevs = []
    processed_titles = []
    while len(processed_titles) < 10:
        movie_id, title = get_random_movie(args.top_movies_only)
        print title
        
        try:
            tw_mean, tw_stddev = title_score(title, heuristic=args.t[0], threshold=args.threshold)
        except NotEnoughTweetsError, e:
            print "Not enough data found to reliably predict score for %s." % title
            continue
        
        processed_titles.append(title)
        
        tw_means.append(tw_mean)
        tw_stddevs.append(tw_stddev)
        
        nf_mean, nf_stddev = nf_title_score(title)
        nf_means.append(nf_mean)
        nf_stddevs.append(nf_stddev)
        
        print "Scoring %s." % title
        print "Twitter mean/variance: %.2f/%.2f" % (tw_mean, tw_stddev)
        print "Netflix mean/variance: %.2f/%.2f" % (nf_mean, nf_stddev)
    
    tw_avg = average(tw_means)
    nf_avg = average(nf_means)
    
    a = map(lambda x: x - tw_avg, tw_means)
    b = map(lambda x: x - nf_avg, nf_means)
    
    a2 = sum(map(lambda x: x ** 2, a))
    b2 = sum(map(lambda x: x ** 2, b))
    
    cov = sum(map(lambda ab: ab[0] * ab[1], zip(a, b)))
    
    correlation = cov / math.sqrt(a2 * b2)
    
    print
    print "Twitter stddev: %.2f" % stddev(tw_means)
    print "Netflix stddev: %.2f" % stddev(nf_means)
    print "Covariance:  %.2f" % cov
    print "Correlation: %.2f" % correlation
    
    if args.normalize:
        mean_diff = average(nf_means) - average(tw_means)
        print "Adjusting twitter means by %.2f (nf avg mean: %.2f; tw avg mean: %.2f)" % (mean_diff, average(nf_means), average(tw_means))
        tw_means = map(lambda mean: mean + mean_diff, tw_means)
    
    if args.plot:
        data    = (tw_means, nf_means)
        errors = (tw_stddevs, nf_stddevs) if args.show_errors else None
        xlabels = map(initials, processed_titles)
        plt = barplot(data, errors=errors, xlabels=xlabels)
        plt.show()
