
import csv
import sqlite3

def connect(dbfile):
    return sqlite3.connect(dbfile)

def load_top_movie_titles(filename):
    with open(filename, 'rb') as csvfile:
        movie_reader = csv.reader(csvfile)
        movie_titles = []
        for (_, _, title) in movie_reader:
            movie_titles.append(title)
    return movie_titles

def mark_movie_title_as_top_movie(conn, title):
    with conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE movies SET top_movie = 1 WHERE title LIKE ?", (title.decode('utf-8'),))

def mark_movie_titles_as_top_movies(conn, titles):
    for title in titles:
        mark_movie_title_as_top_movie(conn, title)

if __name__ == '__main__':
    import sys
    conn = connect('data.db')
    titles = load_top_movie_titles(sys.argv[1])
    mark_movie_titles_as_top_movies(conn, titles)
