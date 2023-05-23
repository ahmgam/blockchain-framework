import queue
from database import Database
from encryption import EncryptionModule
from collections import OrderedDict
import json
class blockchain:
    #initialize the blockchain
    def __init__(self):
        
        # define database manager
        self.db = Database("db.sqlite3","schema.sql")
        # create tables
        self.create_tables()
        # define queue for storing data
        self.genesis_transaction()
 
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
        return item_data
    
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
    
    def __get_current_hash(self,last_transaction_id,item):
        #remove the hash from the record
        current_hash = EncryptionModule.hash(str(last_transaction_id + 1)+json.dumps(item, sort_keys=True))
        return current_hash
    
    def __get_combined_hash(self,current_hash,prev_hash):
        #combine the hashes
        combined_hash = EncryptionModule.hash(current_hash+prev_hash)
        return combined_hash
    #check if the blockchain is valid


    def validate_chain(self):
        pass

    def validate_transaction(self,transaction_id):
        pass
        
    
    ############################################################
    # Syncing the blockchain with other nodes
    ############################################################
    #send sync request to other nodes
    def send_sync_request(self):
        pass
    
    #handle sync request from other nodes
    def handle_sync_request(self):
        pass
    
    def handle_sync_reply(self):
        pass
    
    ############################################################
    # Queue operations
    ############################################################
    def add_to_queue(self, data):
        self.data_queue.put(data)
        
    def get_from_queue(self):
        return self.data_queue.get()

    '''
    import time
import hashlib
import random

# Define constants
NUM_NODES = 4  # including primary
NUM_BACKUPS = NUM_NODES - 1
NUM_FAULTY = 1
LOW_WATER_MARK = 1
HIGH_WATER_MARK = 10
PREPARE_TIMEOUT = 5  # in seconds
MAX_PREPARE_FAILURES = NUM_FAULTY + 1  # f+1
MAX_PREPARE_TIMEOUTS = NUM_FAULTY + 1  # f+1
PREPARE_COLLECT_TIMEOUT = 10  # in seconds
PRIMARY_TIMEOUT_THRESHOLD = 3  # number of prepare timeouts before switching primary

# Define functions for generating keys and signatures
def generate_key():
    return hashlib.sha256(str(random.randint(0, 1000000)).encode('utf-8')).hexdigest()

def sign_message(message, key):
    return hashlib.sha256((message + key).encode('utf-8')).hexdigest()

def verify_signature(message, signature, key):
    return signature == hashlib.sha256((message + key).encode('utf-8')).hexdigest()

# Define classes for nodes and messages
class Node:
    def __init__(self, node_id, is_primary):
        self.node_id = node_id
        self.is_primary = is_primary
        self.key = generate_key()  # generate key for signing messages
        self.log = []  # to store messages
        self.current_view = 0
        self.current_seq_num = 0
        self.current_nst = 0
        self.pending_requests = []  # to store pending client requests
        self.prepared_messages = []  # to store messages for which prepare phase is done
        self.committed_messages = []  # to store messages for which commit phase is done
        self.is_active = False
        self.prepare_failures = 0
        self.prepare_timeouts = 0
        self.primary_timeout_counter = 0

    def send_message(self, message, recipients):
        for recipient in recipients:
            recipient.receive_message(message)

    def receive_message(self, message):
        # Handle prepare-fail message
        if message.startswith("<<prepare-fail"):
            view = int(message.split()[1])
            sigma_p = message.split()[3]
            if view == self.current_view:
                self.switch_to_next_view()

        # Handle prepare-timeout message
        elif message.startswith("<<prepare-timeout"):
            view = int(message.split()[2])
            sigma_p = message.split()[4]
            if view == self.current_view:
                # Extract prepare messages in sigma_p
                prepare_messages = [m for m in self.log if m.startswith("<<pre-prepare") and m.split()[1] == str(view) and m.split()[4] == sigma_p]
                if len(prepare_messages) >= 2*NUM_FAULTY + 1:
                    # There are enough correct prepare messages, so switch to next view
                    self.switch_to_next_view()
                else:
                    # Consensus at prepare stage degenerates to PBFT
                    self.log = []
                    self.prepared_messages = []
                    self.prepare_failures = 0
                    self.prepare_timeouts = 0
                    self.current_seq_num = 0
                    self.current_nst = 0
                    self.primary_timeout_counter = 0
                    self.pending_requests = []
                    self.current_view += 1
                    self.is_primary = (self.node_id == self.current_view % NUM_NODES)
                    self.prepare_phase()

        # Handle prepare-collect message
        elif message.startswith("<<prepare-collect"):
            view = int(message.split()[1])
            seq_num = int(message.split()[2])
            nst = int(message.split()[3])
            sigma_p = message.split()[4]
            if view == self.current_view and nst == self.current_nst:
                prepare_message = "<<pre-prepare " + str(view) + " " + str(seq_num) + " " + str(nst) + " " + sigma_p
                self.log.append(prepare_message)
                self.pending_requests.append(message.split()[5:])
                if len(self.log) == NUM_NODES - NUM_FAULTY:
                    self.prepare_phase()

        # Handle pre-prepare message
        elif message.startswith("<<pre-prepare"):
            view = int(message.split()[1])
            seq_num = int(message.split()[2])
            nst = int(message.split()[3])
            sigma_p = message.split()[4]
            if view == self.current_view and self.is_primary and nst >= self.current_nst:
                preprepare_message = "<<pre-prepare " + str(view) + " " + str(seq_num) + " " + str(nst) + " " + sigma_p
                self.log.append(preprepare_message)
                self.current_seq_num = seq_num
                self.current_nst = nst
                for backup in self.backups:
                    backup.send_message(preprepare_message, self.backups)
                self.prepare_phase()

        # Handle prepare message
        elif message.startswith("<<prepare"):
            view = int(message.split()[1])
            seq_num = int(message.split()[2])
            nst = int(message.split()[3])
            sigma_p = message.split()[4]
            sigma = message.split()[5]
            if view == self.current_view and nst == self.current_nst:
                if verify_signature("<<pre-prepare " + str(view) + " " + str(seq_num) + " " + str(nst) + " " + sigma_p, sigma, self.key):
                    prepare_message = "<<prepare " + str(view) + " " + str(seq_num) + " " + str(nst) + " " + sigma_p + " " + sigma
                    self.log.append(prepare_message)
                    self.prepared_messages.append(prepare_message)
                    if len(self.prepared_messages) == NUM_NODES - NUM_FAULTY:
                        self.commit_phase()

        # Handle commit message
        elif message.startswith("<<commit"):
            view = int(message.split()[1])
            seq_num = int(message.split()[2])
            nst = int(message.split()[3])
            sigma_p = message.split()[4]
            sigma = message.split()[5]
            if view == self.current_view and nst == self.current_nst:
                if verify_signature("<<pre-prepare " + str(view) + " " + str(seq_num) + " " + str(nst) + " " + sigma_p, sigma, self.key):
                    commit_message = "<<commit " + str(view) + " " + str(seq_num) + " " + str(nst) + " " + sigma_p + " " + sigma
                    self.log.append(commit_message)
                    self.committed_messages.append(commit_message)
                    if len(self.committed_messages) == NUM_NODES - NUM_FAULTY:
                        self.execute_requests()

    def prepare_phase(self):
        if self.is_primary:
            prepare_message = "<<pre-prepare " + str(self.current_view) + " " + str(self.current_seq_num) + " " + str(self.current_nst) + "

    '''