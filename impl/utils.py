
import sqlite3
import json
import math

def load_config(config_file):
    f = open('config.json', 'r')
    config = json.loads(f.read())
    f.close()
    return config

def connect():
    return sqlite3.connect('data.db')

def get_random_movies(n, min_year=1990, top_only=False):
    db = connect()
    with db:
        cursor = db.cursor()
        cursor.execute(
            "SELECT * FROM movies WHERE year >= ?%s ORDER BY random() LIMIT ?" % (" AND top_movie = 1" if top_only else ''),
            (min_year, n))
        rows = cursor.fetchall()
        return map(lambda m: (m[0], m[2]), rows)

def get_random_movie(top_only=False):
    return get_random_movies(1, top_only=top_only)[0]

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

def initials(string):
    def first_letter_with_dot(string):
        return string[0] + "."

    return "".join(map(first_letter_with_dot, string.split(" ")))

def batches(l, n):
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

def average(s):
    return sum(s) / float(len(s))

def variance(s):
    mean = average(s)
    return average(map(lambda x: (x - mean)**2, s))

def stddev(s):
    return math.sqrt(variance(s))

def correlation(s1, s2):
    s1_mean = average(s1)
    s2_mean = average(s2)
    a = map(lambda x: x - s1_mean, s1)
    b = map(lambda x: x - s2_mean, s2)
    a2 = sum(map(lambda x: x ** 2, a))
    b2 = sum(map(lambda x: x ** 2, b))
    cov = sum(map(lambda ab: ab[0] * ab[1], zip(a, b)))
    correlation = cov / math.sqrt(a2 * b2)
    
    return correlation

def mean_square_error(predictions, ratings):
    errors = []
    for i in xrange(len(predictions)):
        errors.append((ratings[i] - predictions[i])**2)
    return sum(errors) / len(predictions)

