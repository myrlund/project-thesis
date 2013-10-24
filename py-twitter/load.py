import sqlite3

def connect():
    return sqlite3.connect('data.db')

def load_items():
    f = open('ml/u.item', 'r')
    lines = f.readlines()
    f.close()
    
    movies = []
    for line in lines:
        movies.append(line.strip().split('|'))
    return movies

def batches(l, n):
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

def sqlize(movie):
    cleaner = lambda val: val.strip().replace("'", "''")
    return "'" + "', '".join(['null'] + map(cleaner, movie)) + "'"

def insert_items():
    items = load_items()
    db = connect()
    cursor = db.cursor()
    n = 50
    for batch in batches(items, n):
        sql = "INSERT INTO movies VALUES ("
        sql += "), (".join(map(sqlize, batch))
        sql += ")"
        print "Inserted %d rows." % n
        cursor.execute(sql)
    db.commit()

def load_ratings():
    f = open('ml/u.data', 'r')
    lines = f.readlines()
    f.close()
    
    ratings = []
    for line in lines:
        ratings.append(line.strip().split("\t"))
    return ratings

def insert_ratings():
    ratings = load_ratings()
    db = connect()
    cursor = db.cursor()
    n = 50
    for batch in batches(ratings, n):
        sql = "INSERT INTO ratings VALUES ("
        sql += "), (".join(map(sqlize, batch))
        sql += ")"
        print "Inserted %d rows." % n
        cursor.execute(sql)
    db.commit()

if __name__ == '__main__':
    insert_ratings()
