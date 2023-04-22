import sqlite3

class DatabaseConnection:
    
    def __init__(self, database_url, engine_type='sqlite3'):
        self.database_url = database_url
        if engine_type == 'sqlite3':
            self.engine = sqlite3
            self.connection = sqlite3.connect(database_url)
        self.cursor = self.connection.cursor()
        
    def execute(self, query, params=None):
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            self.connection.commit()
        except Exception as e:
            print(f"error : {e}")
            self.connection.rollback()
            return False
        try:
            return self.cursor.fetchall()
        except:
            return None

    def close(self):
        self.connection.close()
        
    def __del__(self):
        self.close()
    

    