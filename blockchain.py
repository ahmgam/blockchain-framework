import queue
from database import Database
from encryption import EncryptionModule
from collections import OrderedDict
import json
import datetime
from time import mktime
class Blockchain:
    #initialize the blockchain
    def __init__(self,parent):
        
        # define database manager
        self.db = Database("db.sqlite3","schema.sql")
        # create tables
        self.create_tables()
        # define queue for storing data
        self.genesis_transaction()
        #sync timeout
        self.sync_timeout = 10
        #sync views
        self.views = OrderedDict()
        #define parent
        self.parent = parent
 
    ############################################################
    # Database tabels
    ############################################################
    def create_tables(self):
        #create record table
        def_query = """ CREATE TABLE IF NOT EXISTS blockchain (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER  NOT NULL,
            item_table TEXT NOT NULL,
            current_hash TEXT NOT NULL,
            combined_hash TEXT NOT NULL
        );"""
        self.db.query(def_query)

    ############################################################
    # blockchain operations
    ############################################################
    
    #create the genesis transaction
    def genesis_transaction(self):
        #add genesis transaction to the blockchain containing 
        pass
    
    def add_sync_record(self,transaction_record,data_record):
        #add the transaction to the blockchain
        self.db.insert("blockchain",("item_id",transaction_record["id"]),("item_table",transaction_record["item_table"]),("current_hash",transaction_record["current_hash"]),("combined_hash",transaction_record["combined_hash"]))
        #add the data to the blockchain
        self.db.insert(transaction_record["item_table"],*[(key,value) for key,value in data_record.items()])

    #commit a new transaction to the blockchain
    def add_transaction(self,table,data):
        last_transaction_id = self.db.get_last_id("blockchain")
        prev_hash = self.__get_previous_hash(last_transaction_id)
        #add the record to it's table
        item_id = self.db.insert(table,data)
        #get the inserted record
        item = self.db.select(table,["*"],{"id":item_id})[0]
        #remove the hash from the record
        current_hash = self.__get_current_hash(last_transaction_id,item)
        #combine the hashes
        combined_hash = self.__get_combined_hash(current_hash,prev_hash)
        #add the transaction to the blockchain
        self.db.insert("blockchain",("item_id",item_id),("item_table",table),("current_hash",current_hash),("combined_hash",combined_hash))
        return item_id

    def get_transaction(self,transaction_id):
        transaction_data = self.db.select("blockchain",["*"],{"id":transaction_id})[0]
        item_data = self.db.select(transaction_data["item_table"],["*"],{"id":transaction_data["item_id"]})[0]
        return transaction_data,item_data
    
    def get_record(self,table,record_id):
        return self.db.select(table,["*"],{"id":record_id})[0]
    
    def filter_records(self,table,filter):
        return self.db.select(table,["*"],filter)
    
    def get_blockchain(self,start_id=None,end_id = None):
        if start_id is None or start_id < 0:
            start_id = 0
        if end_id is None or end_id > self.db.get_last_id("blockchain"):
            end_id = self.db.get_last_id("blockchain")
        blockchain = []
        for i in range(start_id,end_id+1):
            blockchain.append(self.get_transaction(i))
        return blockchain

    def __get_previous_hash(self,last_transaction_id=None):
        
        if last_transaction_id is None:
            #add genesis transaction, get the hash of auth data
            prev_hash = EncryptionModule.hash(self.parent.auth)
        else:
            #get the hash of last transaction
            prev_hash = self.db.select("blockchain",["combined_hash"],{"id":last_transaction_id})[0]["combined_hash"]
        return prev_hash
    
    def __get_current_hash(self,last_transaction_id,item):
        #remove the hash from the record
        current_hash = EncryptionModule.hash(str(last_transaction_id + 1)+json.dumps(item, sort_keys=True))
        return current_hash
    
    def __get_combined_hash(self,current_hash,prev_hash):
        #combine the hashes
        combined_hash = EncryptionModule.hash(current_hash+prev_hash)
        return combined_hash
    #check if the blockchain is valid


    def validate_chain(self,start_id = None,end_id = None):
        if start_id is None or start_id < 0:
            start_id = 0
        if end_id is None or end_id > self.db.get_last_id("blockchain"):
            end_id = self.db.get_last_id("blockchain")
        for i in range(start_id,end_id+1):
            if not self.validate_transaction(i):
                return False
        return True

    def validate_transaction(self,transaction_id):
        #get the transaction
        transaction_data,item_data = self.get_transaction(transaction_id)
        #get the previous hash
        prev_hash = self.__get_previous_hash(transaction_id-1)
        #get the current hash
        current_hash = self.__get_current_hash(transaction_id,item_data)
        #get the combined hash
        combined_hash = self.__get_combined_hash(current_hash,prev_hash)
        #check if the combined hash is equal to the combined hash in the blockchain
        if combined_hash == transaction_data["combined_hash"]:
            return True
        else:
            return False

        
    
    ############################################################
    # Syncing the blockchain with other nodes
    ############################################################
    #send sync request to other nodes
    def cron(self):
        #TODO implement cron for view timeout
        #check views for timeout
        for view_id,view in self.views.copy().items():
            if mktime(datetime.datetime.now().timetuple()) - view['last_updated'] > self.view_timeout and view['status'] == "pending":
                #evaluate the view
                self.evaluate_view(view_id)
                if self.parent.DEBUG:
                    print(f"View {view_id} timed out, starting evaluation")
              
    def check_sync(self,last_conbined_hash, record_count):
        #check if all input is not null 
        if  last_conbined_hash is None or record_count == 0:
            return True 
   
        #check if last combined hash exists in the blockchain
        last_record = self.db.select("blockchain",["id","combined_hash"],("combined_hash",'==',last_conbined_hash))
        if len(last_record) == 0:
            #if not, then return false
            #end_id = self.db.get_last_id("blockchain")
            #end_hash = self.db.select("blockchain",["combined_hash"],("id",'==',end_id))[0]["combined_hash"]
            return False        
        else:
            #get the id of the last record
            end_id = last_record[0]["id"]

        #check if the number of records is equal to the number of records in the blockchain
        if record_count != self.db.get_last_id("blockchain"):
            return False
        return True
    
        
    def get_sync_info(self):
 
        last_record = self.db.select("blockchain",["combined_hash"],("id",'==',self.db.get_last_id("blockchain")))
        if len(last_record) == 0:
            last_record = None
        else:
            last_record = last_record[0]["combined_hash"]
        number_of_records = self.db.get_last_id("blockchain")
        return last_record,number_of_records
    
    def get_sync_data(self,end_hash,record_count):
        #get end id
 
        end_id = self.db.select("blockchain",["id"],("combined_hash",'==',end_hash))
        if len(end_id) == 0 or end_hash is None:
            end_id = self.db.get_last_id("blockchain")
            start_id = 1
        else:
            end_id = end_id[0]["id"]
            if end_id == self.db.get_last_id("blockchain"):
                return []
            elif end_id != record_count:
                start_id = 1
                end_id = self.db.get_last_id("blockchain")
            else:
                start_id = end_id + 1
                end_id = self.db.get_last_id("blockchain")
        #get the blockchain between start and end id
        blockchain = []
        transactions = self.db.select("blockchain",["*"],("id",">=",start_id),("id","<=",end_id))
        for transaction in transactions:
            #get the item
            item = self.get_record(transaction["item_table"],transaction["item_id"])
            blockchain.append({transaction["id"]:(transaction,item)})
        return blockchain
    
    def send_sync_request(self):
        #get the sync info
        last_record,number_of_records = self.get_sync_info()
        #add sync view
        view_id = EncryptionModule.hash(str(last_record)+str(number_of_records)+str(mktime(datetime.datetime.now().timetuple())))
        self.views[view_id] = {
            "last_updated":mktime(datetime.datetime.now().timetuple()),
            "last_record":last_record,
            "number_of_records":number_of_records,
            "status":"pending",
            "sync_data":[]
        }

        msg = {
            "operation":"sync_request",
            "last_record":last_record,
            "number_of_records":number_of_records,
            "view_id":view_id
        }
        #send the sync request to other nodes
        self.parent.network.send_message('all',msg)

    #handle sync request from other nodes
    def handle_sync_request(self,msg):
        #get last hash and number of records
        node_id = msg["node_id"]
        last_record = msg["message"]["data"]["last_record"]
        number_of_records = msg["message"]["data"]["number_of_records"]
        view_id = msg["message"]["data"]["view_id"]
        #check if the blockchain is in sync
        if self.check_sync(last_record,number_of_records):
            #if it is, then send a sync reply
            msg = {
                "operation":"sync_reply",
                "last_record":last_record,
                "number_of_records":number_of_records,
                "sync_data":self.get_sync_data(last_record,number_of_records),
                "view_id":view_id
            }
            self.parent.network.send_message(node_id,msg)
 
    def handle_sync_reply(self,msg):
        #check if the view exists
        view_id = msg["message"]["data"]["view_id"]
        if view_id in self.views.keys():
            #if it does, then add the sync data to the view
            self.views[view_id]["sync_data"].append(msg["message"]["data"]["sync_data"])
            #check if the number of sync data is equal to the number of nodes
            if len(self.views[view_id]["sync_data"]) == len(self.parent.sessions.get_connection_sessions()):
                self.evaluate_sync_view(view_id)
        else:
            print("view does not exist")

    def evaluate_sync_view(self,view_id):
        #check if the view exists
        if view_id not in self.views.keys():
            print("view does not exist")
            return
        #check if the view is complete
        if self.views[view_id]["status"] != "pending":
            return
        #check if the number of sync data is more than half of the nodes
        if len(self.views[view_id]["sync_data"]) < len(self.parent.sessions.get_connection_sessions())/2:
            print("not enough sync data")
            #mark the view as incomplete
            self.views[view_id]["status"] = "incomplete"
            return

        #loop through the sync data and add them to dictionary
        sync_records = {}
        for data in self.views[view_id]["sync_data"]:
            id = data.keys()[0]
            if id not in sync_records.keys():
                sync_records[id] = []
            sync_records[id].append(data[id])

        #loop through the sync records and check if each key has the same value for all nodes
        sync_data = []
        for id in sync_records.keys():
            #get the first value
            value = sync_records[id][0]
            #check if all the values are the same
            if all(v == value for v in sync_records[id]):
                self.add_sync_record(value[0],value[1])
            else:
                print("sync data is not the same")
                return
        #change the status of the view
        self.views[view_id]["status"] = "complete"
