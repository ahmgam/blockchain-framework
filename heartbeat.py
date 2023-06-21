from collections import OrderedDict
from encryption import EncryptionModule
import datetime
import json
from time import mktime,sleep

class HeartbeatProtocol:
    
    def __init__(self,parent):
        self.parent = parent
        #define heartbeat interval
        self.heartbeat_interval = 5
        #define last heartbeat
        self.last_call = mktime(datetime.datetime.now().timetuple())
    
    def cron(self):
        #send heartbeat to all nodes
        for session_id, session in self.parent.sessions.connection_sessions.items():
            #check if time interval is passed
            session_time = mktime(datetime.datetime.now().timetuple()) - session["last_heartbeat"]
            if session_time > self.heartbeat_interval and session["status"] == "active":
                #send heartbeat
                print("sending heartbeat from cron")
                self.send_heartbeat(session)
                #update last heartbeat time
                self.parent.sessions.connection_sessions[session_id]["last_heartbeat"] = mktime(datetime.datetime.now().timetuple())
    def handle(self,message):
        
        if message.message["type"] == "heartbeat_request":
            if self.parent.DEBUG:
                print(f"Received message from {message.message['node_id']} of type {message.message['type']}, starting handle_heartbeat")
            self.handle_heartbeat(message)
        elif message.message["type"] == "heartbeat_response":
            if self.parent.DEBUG:
                print(f"Received message from {message.message['node_id']} of type {message.message['type']}, starting handle_heartbeat_response")
            self.handle_heartbeat_response(message)
        else:
            if self.parent.DEBUG:
                print(f"unknown message type {message.message['type']}")
                
    
    def send_heartbeat(self,session):
        
        #send heartbeat to session
        #prepare message 
        msg_data = OrderedDict({
                "timestamp": str(datetime.datetime.now()),
                "counter": session["counter"]+1,
                "data":self.parent.sessions.get_node_state_table(),
                "blockchain_status":self.parent.blockchain.get_sync_info()
            })
        #serialize message
        msg_data= json.dumps(msg_data)
        #encrypt message
        encrypted_msg = EncryptionModule.encrypt_symmetric(msg_data,session["key"])
        #create heartbeat message
        payload = OrderedDict({
            "session_id": session["session_id"],
            "node_id": self.parent.node_id,
            "node_type": self.parent.node_type,
            "port": self.parent.port,
            "type": "heartbeat_request",
            "pos": self.parent.pos,
            "message":encrypted_msg
            })
        #serialize message
        msg_data= json.dumps(payload)
        #get message hash and signature
        msg_signature = EncryptionModule.sign(msg_data,self.parent.sk)
        #add hash and signature to message
        payload["signature"] = msg_signature
        #send message
        self.parent.queues.put_queue({"target": session["node_id"],
                        "message": payload,
                        "pos": self.parent.pos},"outgoing")
           
    def handle_heartbeat(self,message):
        #receive heartbeat from node
        #get session
        session = self.parent.sessions.get_connection_sessions(message.message["session_id"])
        if not session:
            if self.parent.DEBUG:
                print("Invalid session")
            return
        #get message hash and signature
        buff = message.message.copy()
        msg_signature = buff.pop("signature")
        #serialize message buffer
        msg_data= json.dumps(buff)
        #verify message signature
        if EncryptionModule.verify(msg_data, msg_signature, EncryptionModule.reformat_public_key(session["pk"])) == False:
            if self.parent.DEBUG:
                print("Invalid signature")
            return
        #decrypt message
        try:
            decrypted_msg = EncryptionModule.decrypt_symmetric(message.message["message"],session["key"])
        except:
            if self.parent.DEBUG:
                print("Invalid key")
            return
        #validate message
        message.message["message"] = json.loads(decrypted_msg)
        #check counter
        if message.message["message"]["counter"]<=session["counter"]:
            if self.parent.DEBUG:
                print("Invalid counter")
            return
        #update node state table
        #self.parent.server.logger.warning(f'table request : {json.dumps(message.message["message"]["data"])}' )
        self.parent.sessions.update_node_state_table(message.message["message"]["data"])
        #chcek blockchain status
        if self.parent.blockchain.check_sync(*message.message["message"]["blockchain_status"]) == False:
            if self.parent.DEBUG:
                print("Un synced blockchain, sending sync request")
            self.parent.blockchain.send_sync_request()
            
        #prepare message 
        msg_data = OrderedDict({
                "timestamp": str(datetime.datetime.now()),
                "counter": session["counter"]+1,
                "data":self.parent.sessions.get_node_state_table(),
                "blockchain_status":self.parent.blockchain.get_sync_info()
            })
        #serialize message
        msg_data= json.dumps(msg_data)
        
        #encrypt message
        encrypted_msg = EncryptionModule.encrypt_symmetric(msg_data,session["key"])
        #create heartbeat message
        payload = OrderedDict({
            "session_id": session["session_id"],
            "node_id": self.parent.node_id,
            "node_type":self.parent.node_type,
            "port": self.parent.port,
            "type": "heartbeat_response",
            "pos": self.parent.pos,
            "message":encrypted_msg
            })
        #serialize message
        msg_data= json.dumps(payload)
        #get message hash and signature
        msg_signature = EncryptionModule.sign(msg_data,self.parent.sk)
        #add hash and signature to message
        payload["signature"] = msg_signature
        #send message
        self.parent.queues.put_queue({"target": session["node_id"],
                        "message": payload,
                        "pos": self.parent.pos},"outgoing")
 
    def handle_heartbeat_response(self,message):
        #receive heartbeat from node
        #get session
        session = self.parent.sessions.get_connection_sessions(message.message["session_id"])
        if not session:
            if self.parent.DEBUG:
                print("Invalid session")
            return
        
        #get message hash and signature
        buff = message.message.copy()
        msg_signature = buff.pop("signature")
        #serialize message buffer
        msg_data= json.dumps(buff)
        #verify message signature
        if EncryptionModule.verify(msg_data, msg_signature, EncryptionModule.reformat_public_key(session["pk"])) == False:
            if self.parent.DEBUG:
                print("Invalid signature")
            return
        #decrypt message
        try:
            decrypted_msg = EncryptionModule.decrypt_symmetric(message.message["message"],session["key"])
        except:
            if self.parent.DEBUG:
                print("Invalid key")
            return
        #validate message
        message.message["message"] = json.loads(decrypted_msg)
        #self.parent.server.logger.warning(f'table response : {json.dumps(message.message["message"]["data"])}' )
        #check counter
        if message.message["message"]["counter"]<session["counter"]:
            if self.parent.DEBUG:
                print("Invalid counter")
            return
        #update node state table
        self.parent.sessions.update_node_state_table(message.message["message"]["data"])
        #update session
        self.parent.sessions.update_connection_session(message.message["session_id"],{
            "counter":message.message["message"]["counter"],
            "last_active": mktime(datetime.datetime.now().timetuple())})   
        #chcek blockchain status
        if self.parent.blockchain.check_sync(*message.message["message"]["blockchain_status"]) == False:
            if self.parent.DEBUG:
                print("Un synced blockchain, sending sync request")
            self.parent.blockchain.send_sync_request()    
      