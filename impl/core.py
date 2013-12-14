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

def get_tweets(query, result_type, max_tweets):
    # Search the Twitter API for the given title
    twitter_client = Twitter(CONFIG['twitter'])
    tweet_data = twitter_client.search("\"%s\" movie -download -stream -#nw -#nowwatching -RT" % (query,), result_type=result_type, count=max_tweets)
    
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

def generate_ratings(title, source_type, threshold, max_tweets):
    tweets = get_tweets(title, source_type, max_tweets)
    if len(tweets) < threshold:
        raise NotEnoughTweetsError("Number of tweets below threshold of %d." % threshold)
    
    sentiments = get_sentiments(tweets)
    weights = weigh_sentiments(sentiments)
    return weights

def analyze_ratings(ratings):
    mean = average(ratings)
    var = stddev(ratings)
    return mean, var

def title_score(title, heuristic='popular', threshold=5, max_tweets=25):
    ratings = generate_ratings(title, source_type=heuristic, threshold=threshold, max_tweets=max_tweets)
    return analyze_ratings(ratings)

def netflix_average_rating(title):
    return average(netflix.ratings_for_movie_title(title))

def nf_title_score(title):
    ratings = netflix.ratings_for_movie_title(title)
    return analyze_ratings(ratings)

def means_of_random_movies(n_titles, twitter_search_type=None, top_movies_only=False, tweet_threshold=5, max_tweets=25):
    means = []
    stddevs = []
    processed_titles = []
    while len(processed_titles) < n_titles:
        movie_id, title = get_random_movie(args.top_movies_only)
        
        if DEBUG: print title
        
        try:
            mean, stddev = title_score(title, heuristic=twitter_search_type, threshold=tweet_threshold, max_tweets=max_tweets)
        except NotEnoughTweetsError, e:
            print "Not enough data found to reliably predict score for %s." % title
            continue
        
        processed_titles.append(title)
        means.append(mean)
        stddevs.append(stddev)
        
        if DEBUG:
            print "Twitter mean/variance: %.2f/%.2f" % (mean, stddev)
            print
    
    return (means, stddevs, processed_titles)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Parses sentences.")
    parser.add_argument('-t', help="type of search", choices=('recent', 'popular', 'mixed'), default='popular')
    parser.add_argument('-n', help="number of movies to process", type=int, default=10)
    parser.add_argument('--max-tweets', help="max number of tweets to process per title", type=int, default=25)
    parser.add_argument('--threshold', help="number of tweets required to start sentiment analysis", type=int, default=5)
    parser.add_argument('--normalize', action='store_true', help="normalize twitter ratings to match average mean of netflix data")
    parser.add_argument('--top-movies-only', action='store_true', help="only load top movies")
    parser.add_argument('--plot', action='store_true', help="plot the results and show them")
    parser.add_argument('--show-errors', action='store_true', help="plot the standard deviations and other errors")
    parser.add_argument('-d', '--debug', action='store_true', help="print traces and parse trees")
    parser.add_argument('routine', choices=('mse', 'compare'), nargs='?', default='mse')

    args = parser.parse_args()
    DEBUG = args.debug
    
    if args.routine == "mse":
        
        N = args.n
        
        # Calculate rating means of random movies
        (predictions, stddevs, titles) = means_of_random_movies(N, twitter_search_type=args.t,
                                                                   top_movies_only=args.top_movies_only,
                                                                   tweet_threshold=args.threshold,
                                                                   max_tweets=args.max_tweets)
        
        ratings = map(netflix_average_rating, titles)
        print "Ratings:\n%s" % "\n".join(map(lambda r: "%.2f" % r, ratings))
        
        mae_predictions = mean_average_error(predictions, ratings)
        
        print "Correlation: %.2f" % correlation(predictions, ratings)
        print "Mean Average Error: %.2f" % mae_predictions
        print "Average of actual ratings (baseline): %.2f" % mean_average_error([average(ratings)] * N, ratings)
        
    
    if args.routine == "compare":
        
        # Calculate rating means of random movies
        (means, stddevs, processed_titles) = means_of_random_movies(args.n, twitter_search_type=args.t,
                                                                            top_movies_only=args.top_movies_only,
                                                                            tweet_threshold=args.threshold)
        
        # Unpack scores
        tw_means, tw_stddevs = means, stddevs
    
        # Get netflix ratings
        netflix_scores = map(nf_title_score, processed_titles)
        nf_means, nf_stddevs = zip(*netflix_scores)
    
        correlation_coefficient = correlation(tw_means, nf_means)
    
        if DEBUG:
            print "Twitter stddev: %.2f" % stddev(tw_means)
            print "Netflix stddev: %.2f" % stddev(nf_means)
            print "Correlation: %.2f" % correlation_coefficient
    
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
