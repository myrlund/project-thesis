import sqlite3
import csv

def connect():
    return sqlite3.connect('data_nf.db')

def load_movie_titles():
    f = open('nf/movie_titles.txt', 'rb')
    lines = f.readlines()
    f.close()
    
    process = lambda s: s.strip().decode('iso-8859-1')
    
    movies = []
    for line in lines:
        # movie ~ (movie_id, year, title)
        movie = map(process, line.split(",", 2))
        movies.append(movie)
    
    return movies

def insert_movie_titles(movies):
    conn = connect()
    with conn:
        cursor = conn.cursor()
        
        cursor.execute("DROP TABLE IF EXISTS movies")
        cursor.execute("CREATE TABLE movies (id INT, year VARCHAR(4), title VARCHAR(150))")
        cursor.executemany("INSERT INTO movies VALUES (?, ?, ?)", movies)

def get_id_for_title(title):
    conn = connect()
    with conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM movies WHERE title LIKE ?", (title,))
        rows = cursor.fetchall()
        
        if len(rows) > 0:
            return rows[0][0]
        else:
            return None

def load_movie_rating_items(movie_id):
    filename = "nf/training_set/mv_%07d.txt" % int(movie_id)
    
    f = open(filename, 'rb')
    lines = f.readlines()
    f.close()
    
    ratings = []
    for rating_row in lines[1:]:
        rating = [unicode(movie_id)] + rating_row.strip().split(",", 2)
        ratings.append(rating)
    
    return ratings

def insert_movie_ratings(ratings):
    conn = connect()
    with conn:
        cursor = conn.cursor()
        
        cursor.execute("CREATE TABLE IF NOT EXISTS ratings (id INT, movie_id INT, user_id INT, rating TINYINT, rate_date DATE)")
        cursor.execute("DELETE FROM ratings WHERE movie_id = ?", (ratings[0][0],))
        cursor.executemany("INSERT INTO ratings VALUES (NULL, ?, ?, ?, ?)", ratings)

def load_movie_ratings(movie_id):
    filename = "nf/training_set/mv_%07d.txt" % int(movie_id)
    
    f = open(filename, 'rb')
    lines = f.readlines()
    f.close()
    
    ratings = []
    for rating_row in lines[1:]:
        rating = float(rating_row.split(",", 2)[1])
        ratings.append(rating)
    
    return ratings

def ratings_for_movie_title(title):
    movie_id = get_id_for_title(title)
    return load_movie_ratings(movie_id)

if __name__ == '__main__':
    # movies = load_movie_titles()
    # insert_movie_titles(movies)
    
    ratings = ratings_for_movie_title("pulp fiction")
    print sum(ratings) / len(ratings)
    
    # for movie_id in xrange(1, 17770 + 1):
    #     ratings = load_movie_ratings(movie_id)
    #     insert_movie_ratings(ratings)
    #     print "Inserted movie #%d" % movie_id
    
    print "Done"
