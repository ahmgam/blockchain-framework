from random import choices
from string import ascii_lowercase
import json
from encryption import EncryptionModule
from math import ceil
class SBFT:
    def __init__(self,parent) -> None:
        #define parent
        self.parent = parent
        #define views
        self.views = {}
        
    def handle(self, msg):
        #handle message
        operation = msg['operation']
        if operation == 'pre-prepare':
            self.pre_prepare(msg)
        elif operation == 'prepare':
            self.prepare(msg)
        elif operation == 'prepare-collect':
            self.prepare_collect(msg)
        elif operation == 'commit':
            self.commit(msg)
        elif operation == 'commit-collect':
            self.commit_collect(msg)
        else:
            print(f"Received message from {msg['message']['node_id']} of type {msg['message']['type']}, but no handler found")
        pass
    
    def send(self,msg):
        #check message type 
        if type(msg['message']) != dict:
            if self.parent.DEBUG:
                print("Invalid message type")
            return
        #create view number 
        view_id = self.generate_view_id()
        #stringify message 
        msg_string = json.dumps(msg['message'])
        #get message hash 
        msg_hash = EncryptionModule.hash(msg_string)
        #get node_ids 
        node_ids = self.parent.sessions.get_active_nodes()
        node_ids.append(self.parent.node_id)
        #create view
        self.views[view_id] = {
            "source": self.parent.node_id,
            "message":msg['message'],
            "prepare":[],
            "commit":[],
            "view_id":view_id,
            "status":"prepare",
            "hash": msg_hash,
            "node_ids":node_ids
            }
        #add view to message
        msg['view_id'] = view_id
        #sign message
        msg_signature = EncryptionModule.sign_hash(msg_hash,self.parent.sk)
        #add signature to message
        msg["signature"] = msg_signature
        #add node_ids to message
        msg["node_ids"] = node_ids
        #broadcast message to the network
        self.parent.network.send_message(node_ids,msg)
    
    def pre_prepare(self,msg):
        #handle pre-prepare message
        #check if view exists
        view_id = msg['view_id']
        if view_id in self.views.keys():
            if self.parent.DEBUG:
                print("View is already created")
            return
        #get the session 
        session = self.parent.sessions.get_connection_sessions(msg['source'])
        #verify signature
        msg_signature = msg.pop('signature')
        #stringify the data payload
        msg_data = json.dumps(msg["message"])
        #verify the message signature
        if EncryptionModule.verify(msg_data, msg_signature, EncryptionModule.reformat_public_key(session["pk"])) == False:
            if self.parent.DEBUG:
                print("signature not verified")
            return None
        
        #message payload
        payload = {
            "operation":"prepare",
            "source":self.parent.node_id,
            "view_id":view_id
        }
        #get hash and sign of message
        msg_data = json.dumps(payload)
        msg_hash = EncryptionModule.hash(msg_data)
        msg_signature = EncryptionModule.sign_hash(msg_hash,self.parent.sk)
        #add signature to message
        payload["hash"]=msg_hash
        payload["signature"]=msg_signature
        #create view
        self.views[view_id] = {
            "source": msg['source'],
            "message":msg['message'],
            "prepare":[],
            "commit":[],
            "view_id":view_id,
            "status":"prepare",
            "hash": msg_hash,
            "node_ids":msg['node_ids']
        }
        
        #send_message
        self.parent.network.send_message(msg['source'],payload)
    
    def prepare(self,msg):
        #handle prepare message
        #check if view exists
        view_id = msg['view_id']
        if view_id not in self.views.keys():
            if self.parent.DEBUG:
                print("View is not created")
            return
        #get view 
        view = self.views[view_id]
        #get session
        session = self.parent.sessions.get_connection_sessions(msg['source'])
        #check if current node_id is in node_ids
        if self.parent.node_id not in view['node_ids']:
            if self.parent.DEBUG:
                print("Node_id not in node_ids")
            return
        #check if node_id is not the source
        if self.parent.node_id == msg['source']:
            if self.parent.DEBUG:
                print("Node_id is the source")
            return
        #verify signature
        msg_signature = msg.pop('signature')
        #stringify the data payload
        msg_data = json.dumps(view["message"])
        #verify the message signature
        if EncryptionModule.verify(msg_data, msg_signature, EncryptionModule.reformat_public_key(session["pk"])) == False:
            if self.parent.DEBUG:
                print("signature not verified")
            return None
        #check hash of message
        if msg["hash"] != view["hash"]:
            if self.parent.DEBUG:
                print("Hash of message does not match")
            return None
        #add message to prepare
        self.views[view_id]["prepare"].append(msg)
        #check if the number of prepare is more than 
        if len(self.views[view_id]["prepare"]) < ceil((2/3)*((len(view["node_ids"])-1)/3)):
            return None
        #send prepare-collect message to source node
        payload = {
            "operation":"prepare-collect",
            "view_id":view_id,
            "source":self.parent.node_id,
            "prepare":self.views[view_id]["prepare"]
        }
        #get hash and sign of message
        msg_data = json.dumps(payload)
        msg_hash = EncryptionModule.hash(msg_data)
        msg_signature = EncryptionModule.sign_hash(msg_hash,self.parent.sk)
        #add signature to message
        payload["signature"] = msg_signature
        #broadcast message
        self.parent.network.send_message(view["node_ids"],payload)
        
    
    def prepare_collect(self,msg):
        #handle prepare-collect message
        #check if view exists
        view_id = msg['view_id']
        if view_id not in self.views.keys():
            if self.parent.DEBUG:
                print("View is not created")
            return
        #get view 
        view = self.views[view_id]
        #get session
        session = self.parent.sessions.get_connection_sessions(msg['source'])
        #check if current node_id is in node_ids
        if self.parent.node_id not in view['node_ids']:
            if self.parent.DEBUG:
                print("Node_id not in node_ids")
            return
        #check if node_id is not the source
        if self.parent.node_id == msg['source']:
            if self.parent.DEBUG:
                print("Node_id is the source")
            return
        #verify signature
        msg_signature = msg.pop('signature')
        #stringify the data payload
        msg_data = json.dumps(msg["message"])
        #verify the message signature
        if EncryptionModule.verify(msg_data, msg_signature, EncryptionModule.reformat_public_key(session["pk"])) == False:
            if self.parent.DEBUG:
                print("signature not verified")
            return None
        #check hash of message
        msg_hash = EncryptionModule.hash(msg_data)
        if msg_hash != view["hash"]:
            if self.parent.DEBUG:
                print("Hash of message does not match")
            return None
        #get message data from view
        msg_view_data = json.loads(view["message"])
        #loop in prepare-collect
        for m in msg["prepare"]:
            #get session
            m_session = self.parent.sessions.get_connection_sessions(m['source'])
            #verify signature
            m_signature = m.pop('signature')
            #verify the message signature
            if EncryptionModule.verify(msg_view_data, m_signature, EncryptionModule.reformat_public_key(m_session["pk"])) == False:
                if self.parent.DEBUG:
                    print("signature not verified")
                return None
            #check hash of message
            if m["hash"] != view["hash"]:
                if self.parent.DEBUG:
                    print("Hash of message does not match")
                return None
        #send commit message to source node
        payload = {
            "operation":"commit",
            "view_id":view_id,
            "source":self.parent.node_id
        }
        #get hash and sign of message
        msg_data = json.dumps(payload)
        msg_hash = EncryptionModule.hash(msg_data)
        msg_signature = EncryptionModule.sign_hash(msg_hash,self.parent.sk)
        #add signature to message
        payload["signature"] = msg_signature
        self.parent.network.send_message(view["source"],payload)
    def commit(self,msg):
        #handle commit message
        pass
    
    def commit_collect(self,msg):
        #handle commit-collect message
        pass
    
    def generate_view_id(self,length=8):
        #generate view id
        return ''.join(choices(ascii_lowercase, k=length))
    
