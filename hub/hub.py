import sqlite3
from flask import Flask, request, Response,jsonify
import os
import datetime
import requests
import json
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
    
    
class Hub :
    def __init__(self):
        #get the path of the database from environment variable
        if 'HUB_DB' in os.environ:    
            self.path = os.environ['HUB_DB']
        else:
            self.path = 'hub\database.db'
        #get the path of the schema from environment variable if it exists
        if 'HUB_SCHEMA' in os.environ:
            self.schema = os.environ['HUB_SCHEMA']
        else:
            self.schema = None
        
        if 'HUB_PORT' in os.environ:
            self.port = os.environ['HUB_PORT']
        else:
            self.port = 5000
            
        if 'HUB_AUTH' in os.environ:
            self.auth = os.environ['HUB_AUTH']
        else:        
            self.auth = None
        #initialize the database
        self.db = Database(self.path, self.schema)
        #initialize the flask app
        self.app = Flask(__name__)
        #add url rules
        self.app.add_url_rule('/', 'index', lambda : self.index(self), methods=['POST', 'GET'])
        self.app.add_url_rule('/reset', 'reset', lambda : self.reset(self), methods=['POST', 'GET'])
        self.app.add_url_rule('/status', 'status', lambda : self.status(self), methods=['POST', 'GET'])
        self.app.run(port=self.port)
      
    @staticmethod    
    def index(self):
        #check if the request header contains the correct authentication token
        if not self.is_authenticated(request):
            return jsonify({'error': 'unauthorized'}, 401)
            
        #get the request body and convert it to a dictionary    
        data = request.json
        #validate the request
        valid,resp = self.validate_request(data)
        if not valid:
            return resp
        #get target and message from the request body
        target_id = data['target']
        message = data['message']
        pos = data["pos"]
        self.app.logger.warning(f"Received message from {message['node_id']} to {target_id} with content {message['message']} and position {pos} at {datetime.datetime.now()}")
        #check if the node is already registered
        node = self.get_node(message['node_id'])
        if not node:
            self.register_node(message['node_id'],message['node_type'],request.remote_addr,message['port'],message.get('pk', None))
        else:
            self.update_node(message['node_id'],message['node_type'],request.remote_addr, message['port'], message.get('pk', None))
        #add the node's position to the state table
        self.add_state(message['node_id'], message['node_type'], pos)
        #store the message in the database
        msg = self.store_message(message['node_id'], message['node_type'], target_id, message['message'])   
        #check if target node is registered
        if target_id != 'all':
            target = self.get_node(target_id)
            #self.app.logger.warning(target)
            if not node:
                return jsonify({'error': 'node not found'}, 404)
            #send the message to the target node
            try : 
                self.deliver_message(message,target["ip"],target["port"])
                #update served flag in message record
                self.mark_message(msg)
                return jsonify({'success': 'message sent'})
            except:
                return jsonify({'error': 'message received but not delivered'})
        else:
            #send the message to all nodes
            print(" brodcasting message")
            self.brodcast_message(message,message['node_id'])
            print(" brodcasted message")
            self.mark_message(msg)
            print(" marked message")
            return jsonify({'success': 'message brodcasted'})

    @staticmethod
    def reset(self,request):
        if not self.is_authenticated(request):
            return jsonify({'error': 'unauthorized'}, 401)
        #clear the database
        self.db.query('DELETE FROM node')
        self.db.query('DELETE FROM message')
        self.db.query('DELETE FROM state')
        return jsonify({'success': 'reset'}, 200)
    
    @staticmethod
    def status(self,request):
        if not self.is_authenticated(request):
            return jsonify({'error': 'unauthorized'}, 401)
        #get the status of the hub
        nodes = self.db.query('SELECT * FROM node')
        messages = self.db.query('SELECT * FROM message')
        states = self.db.query("SELECT * FROM state WHERE timestamp > datetime(\'now\', \'-1 day\')")
        return jsonify({'nodes': nodes, 'messages': messages, 'states': states}, 200)
     
    def is_authenticated(self, request):
        #check if the request header contains the correct authentication token
        if request.headers.get('Authorization') == self.auth or self.auth == None:
            return True
        elif request.headers.get('Authorization') == None:
            return False    
        

    def validate_request(self,data):
        if not ('target' in data.keys()):
            return False,jsonify({'error': 'target not found'})
        if not ('message' in data.keys()):
            return False,jsonify({'error': 'message not found'})
        if not ('pos' in data.keys()):
            return False,jsonify({'error': 'pos not found'})
        if not ('node_id' in data['message'].keys()):
            return False,jsonify({'error': 'node_id not found in message'})
        if not ('node_type' in data['message'].keys()):
            return False,jsonify({'error': 'node_type not found in message'})
        if not ('port' in data['message'].keys()):
            return False,jsonify({'error': 'port not found in message'})
        if not ('message' in data['message'].keys()):
            return False,jsonify({'error': 'message not found in message'})
        
        return True,None
        

    def get_node(self, node_id):
        #check if the node is registered
        node = self.db.query('SELECT * FROM node WHERE node_id = ?', (node_id,))
        if not node:
            return False
        else:
            return node[0]
        
    def register_node(self, node_id, node_type, ip, port, pk):
        #register a new node
        self.db.query('INSERT INTO node (node_id, node_type, ip, port, pk) VALUES (?, ?, ?, ?, ?)', 
                      (node_id,
                       node_type,
                       ip,
                       port,
                       pk))
    def update_node(self, node_id, node_type, ip, port, pk):
        #update node information
        self.db.query('UPDATE node SET node_type = ?, ip = ?, port = ?, pk = ?, last_active = ? WHERE node_id = ?', 
                          (node_type, 
                           ip,
                           port,
                           pk,
                           datetime.datetime.now(),
                           node_id))
        
    def add_state(self, node_id, node_type, pos):
        #add node position to state table
        self.db.query('INSERT INTO state (node_id, node_type, node_position, timecreated) VALUES (?, ?, ?, ?)',
                        (node_id,
                         node_type,
                         json.dumps(pos),
                         datetime.datetime.now()))
        
    def store_message(self, node_id, target, type, data):
        #store a message in the database
        msg =self.db.query('INSERT INTO message (node_id, target, type, data) VALUES (?, ?, ?, ?)', 
                      (node_id,
                       target,
                       type,
                       json.dumps(data)))
        return msg
    
    def deliver_message(self, message,target_ip,target_port):
        #deliver a message to the target node
        req = requests.post('http://'+target_ip+':'+str(target_port)+'/', json=message, timeout=1)
        if req.status_code == 200:
            return True
        else:
            return False
            
    def mark_message(self, message_id):
        #mark a message as served
        self.db.query('UPDATE message SET served = 1 WHERE id = ?', (message_id,))
        
    def brodcast_message(self, message,exclude=None):
        #send a message to all nodes
        nodes = self.db.query('SELECT * FROM node')
        for node in nodes:
            try:
                if (node['node_id'] == exclude):
                    continue
                print(" brodcasting message to ",node['node_id'])
                self.deliver_message(message, node['ip'], node['port'])
            #handle timeout errors
            except requests.exceptions.ConnectionError:
                self.app.logger.warning('timeout error, node not found')
                self.db.query('DELETE FROM node WHERE node_id = ?', (node['node_id'],))
if __name__ == '__main__':
    #set environment variables
    os.environ['HUB_DB'] = 'hub\database.db'
    os.environ['HUB_SCHEMA'] = 'hub\schema.sql'
    os.environ['HUB_PORT'] = '5000'
    os.environ['HUB_AUTH'] = '1234567890'
    #run the hub
    app = Hub()