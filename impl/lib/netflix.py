import sqlite3

def connect():
    return sqlite3.connect('data.db')

def load_movie_titles():
    f = open('netflix/movie_titles.txt', 'rb')
    lines = f.readlines()
    f.close()
    
    process = lambda s: s.strip().decode('iso-8859-1')
    
    movies = []
    for line in lines:
        # movie ~ (movie_id, year, title)
        movie = map(process, line.split(",", 2))
        movies.append(movie)
    
    return movies

def seed_movie_titles(movies):
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

def load_movie_ratings(movie_id):
    filename = "netflix/training_set/mv_%07d.txt" % int(movie_id)
    
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
    if movie_id is not None:
        return load_movie_ratings(movie_id)
    else:
        return None

if __name__ == '__main__':
    # Uncomment for seeding of movies
    # seed_movie_titles(load_movie_titles())
    
    import sys
    title = " ".join(sys.argv[1:])
    ratings = ratings_for_movie_title(title)
    print "Average rating for %s: %.2f" % (title, sum(ratings) / len(ratings))
