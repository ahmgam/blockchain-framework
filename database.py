import sqlite3
import random
class Database (object):
    def __init__(self, path, schema=None):
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = Database.dict_factory
        if schema:
            with open(schema) as f:
                self.connection.executescript(f.read())
        self.cursor = self.connection.cursor()
        self.tabels = self.__get_db_meta()

    def __get_db_meta(self):
        cols = self.query("""
        SELECT 
        m.name as table_name, 
        p.name as column_name,
        p.type as column_type,
        p.'notnull' as not_null
        FROM 
        sqlite_master AS m
        JOIN 
        pragma_table_info(m.name) AS p
        WHERE
        m.type = 'table' 
        ORDER BY 
        m.name, 
        p.cid
        """)
        tabels = {table_name : {"name":table_name,"columns":{}} for table_name in set([col['table_name'] for col in cols])}
        # add columns to tabels
        for col in cols:
            tabels[col['table_name']]["columns"][col['column_name']]=({"name":col['column_name'],"type":col['column_type'], "not_null":col['not_null']})

        #remove sqlite_sequence table
        tabels.pop("sqlite_sequence",None)
        #replace type with python type
        for table_name,table_content in tabels.items():
            for column in table_content["columns"].values():
                if column["type"] == "INTEGER":
                    tabels[table_name]["columns"][column["name"]]["type"] = int
                elif column["type"] == "REAL":
                    tabels[table_name]["columns"][column["name"]]["type"] =float
                elif column["type"] == "TEXT":
                    tabels[table_name]["columns"][column["name"]]["type"] = str
                elif column["type"] == "BLOB":
                    tabels[table_name]["columns"][column["name"]]["type"] = bytes
                else:
                    raise Exception("Column type not supported")
        return tabels
    def __del__(self):
        self.connection.close()

    def __table_exists(self,table_name):
        return table_name in self.tabels.keys()
    
    def __column_exists(self,table_name,column_name):
        return column_name in self.tabels[table_name]["columns"].keys() or column_name=="*"
    
    def __check_fields_format(self,fields):
        if not type(fields) in [list,tuple]:
            raise Exception("Column must be a list or tuple")
        if len(fields) != 2:
            raise Exception("Column must have 2 elements")

    def __check_condition_format(self,conditions):
        if not type(conditions) in [list,tuple]:
            raise Exception("Column must be a list or tuple")
        if len(conditions) != 3:
            raise Exception("Column must have 3 elements")
         
    def __check_column_options(self,column):
        if not column[1] in ["==",">=","<=",">","<","!=","LIKE","NOT LIKE","IN","NOT IN","IS","IS NOT","BETWEEN","NOT BETWEEN","NULL","NOT NULL"]:
            raise Exception("Column type not supported")
        
    def __check_column_type(self,table,column,value):
        if not type(value) in [int,float,str,bytes,bool,None]:
            raise Exception(f"Column type not supported : {type(value)}")
        if str(value).isnumeric():
            return
        if not type(value) == self.tabels[table]["columns"][column]["type"]:
            raise Exception(f"Wrong data type for {column} ,data type : {type(value)} , expected : {self.tabels[table]['columns'][column]['type']}")
        
    def insert(self,table_name,*keywords):
        #check if table exists
        if not self.__table_exists(table_name):
            raise Exception(f"Table does not exists : {table_name}")
        #check if fields format is valid
        for keyword in keywords:
            self.__check_fields_format(keyword)
        #check if fields are valid
        for keyword,value in keywords:
            if not self.__column_exists(table_name,keyword):
                raise Exception(f"Column does not exists : {keyword}")
            self.__check_column_type(table_name,keyword,value)

        #build query
        query = "INSERT INTO {table} ({keywords}) VALUES ({values})".format(
            table=table_name,keywords=",".join(keyword[0] for keyword in keywords),
            values=",".join(["?" for i in range(len(keywords))])
            )
        #execute query
        return self.query(query,tuple([keyword[1] for keyword in keywords]))
        
    def select(self,table_name,fields,*conditions):
        
        #check if table exists
        if not self.__table_exists(table_name):
            raise Exception(f"Table does not exists : {table_name}")
        #check if fields exists
        if type(fields) == str:
            fields = [fields]
        for field in fields:
            if not self.__column_exists(table_name,field):
                raise Exception(f"Column does not exists : {field}")
        #check if conditions are valid
        for condition in conditions:
            self.__check_condition_format(condition)
            if not self.__column_exists(table_name,condition[0]):
                raise Exception(f"Column does not exists : {condition[0]}")
            self.__check_column_options(condition)
            self.__check_column_type(table_name,condition[0],condition[2])
       
        #build query
        query = "SELECT {fields} FROM {table} {options}".format(
            fields=",".join(fields),table=table_name,
            options="WHERE "+" AND ".join([f"{condition[0]} {condition[1]} ?" for condition in conditions]) if conditions else ""
            )
        #execute query
        return self.query(query,tuple([condition[2] for condition in conditions]))
    
    def delete(self,table_name,*conditions):

        #check if table exists
        if not self.__table_exists(table_name):
            raise Exception(f"Table does not exists : {table_name}")

        #check if conditions are valid
        for condition in conditions:
            self.__check_condition_format(condition)
            if not self.__column_exists(table_name,condition[0]):
                raise Exception(f"Column does not exists : {condition[0]}")
            self.__check_column_options(condition)
            self.__check_column_type(table_name,condition[0],condition[2])

        #build query
        query = "DELETE FROM {table} {options}".format(
            table=table_name,
            options="WHERE "+" AND ".join([f"{condition[0]} {condition[1]} ?" for condition in conditions]) if conditions else ""
            )
        #execute query
        return self.query(query,tuple([condition[2] for condition in conditions]))
    
    def update(self,table_name,*conditions,**keyword):

        #check if table exists
        if not self.__table_exists(table_name):
            raise Exception(f"Table does not exists : {table_name}")
        #check if conditions are valid
        for condition in conditions:
            self.__check_condition_format(condition)
            if not self.__column_exists(table_name,condition[0]):
                raise Exception(f"Column does not exists : {condition[0]}")
            self.__check_column_options(condition)
            self.__check_column_type(table_name,condition[0],condition[2])
        #check keywords
        for key,value in keyword.items():
            if not self.__column_exists(table_name,key):
                raise Exception(f"Column does not exists : {key}")
            self.__check_column_type(table_name,key,value)

        #build query
        query = "UPDATE {table} SET {keywords} {options}".format(
            table=table_name,
            keywords=",".join([f"{key} = ?" for key in keyword]),
            options="WHERE "+" AND ".join([f"{condition[0]} {condition[1]} ?" for condition in conditions]) if conditions else ""
            )
        print(query)
        #execute query
        return self.query(query,tuple([value for value in keyword.values()]+[condition[2] for condition in conditions]))
    
    def count(self,table_name,*conditions):
        
        #check if table exists
        if not self.__table_exists(table_name):
            raise Exception(f"Table does not exists : {table_name}")
        #check if conditions are empty
        if not conditions:
            return self.query(f"SELECT COUNT(*) FROM {table_name}")
        #check if conditions are valid
        for condition in conditions:
            self.__check_condition_format(condition)
            if not self.__column_exists(table_name,condition[0]):
                raise Exception(f"Column does not exists : {condition[0]}")
            self.__check_column_options(condition)
            self.__check_column_type(table_name,condition[0],condition[2])
       
        #build query
        query = "SELECT COUNT(*) FROM {table} {options}".format(
            table=table_name,
            options="WHERE "+" AND ".join([f"{condition[0]} {condition[1]} ?" for condition in conditions]) if conditions else ""
            )
        #execute query
        return self.query(query,tuple([condition[2] for condition in conditions]))
 
    def get_last_id(self,table_name):
        #check if table exists
        if not self.__table_exists(table_name):
            raise Exception(f"Table does not exists : {table_name}")
        #check if table is empty
        if not self.query(f"SELECT * FROM {table_name}"):
            return 0
        return self.query(f"SELECT MAX(id) FROM '{table_name}'")[0]['MAX(id)']
    
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

if __name__=="__main__":
    db = Database("db.sqlite3","schema.sql")
    print(db.insert("states",("node_id",str(random.randint(0,1000))),("node_type","uav" if random.randint(1,10) %2 == 1 else "ugv"),("timecreated","123456789"),("pos_x",0.0),("pos_y",0.0),("details","")))
    print(db.select("states","*",("node_type","==","uav")))
    db.delete("states",("node_type","==","ugv"))
    print(db.select("states","*"))
    db.update("states",("node_type","==","uav"),node_type="rov")
    print(db.get_last_id("states"))