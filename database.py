import sqlite3

class Database (object):
    def __init__(self, path, schema=None):
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = Database.dict_factory
        if schema:
            with open(schema) as f:
                self.connection.executescript(f.read())
        self.cursor = self.connection.cursor()

    def __del__(self):
        self.connection.close()

    def initialize(self, path):
        with open(path) as f:
            self.connection.executescript(f.read())
            
    def query(self, query, args=()):    
        self.cursor.execute(query, args)
        self.connection.commit()        
        return self.cursor.lastrowid if query.startswith('INSERT') else  self.cursor.fetchall()
    
    @staticmethod
    def dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    