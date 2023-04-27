import requests
from flask import Flask, Response,request
from messages import *
import datetime
from encryption import EncryptionModule
     
class NetworkInterface:
    
    def __init__(self,parent):
        '''
        Initialize network interface
        '''
        #define parent
        self.parent = parent
        #define discovery interval
        self.discovery_interval = 10
        #define heartbeat interval
        self.heartbeat_interval = 5
        #define listening flask
        self.server = Flask(__name__)
        #disable logging if not in debug mode
        if not self.parent.DEBUG:
            self.server.logger.disabled = True
        self.server.add_url_rule('/', 'listen',lambda : self.listen(self), methods=['POST'])
        #add message send endpoint
        self.server.add_url_rule('/send', 'send',lambda : self.send(self), methods=['POST'])
        #self.server.add_url_rule('/', 'listen',self.listen, methods=['POST'])
   
    @staticmethod 
    def send(self):
        '''
        Send message to the given public key
        '''
        #get data 
        data = request.json
        message = data["message"]
        #payload 
        payload = {
            "operation":"pre-prepare",
            "message":message
        }
        #send_message
        self.parent.consensus.send(payload)
        return Response("OK", status=200)
    
    @staticmethod
    def listen(self):
        '''
        receive message from the network
        '''
        #receive message from the network and put it in the queue
        self.parent.queues.put_queue(request.json,"incoming")
        return Response("OK", status=200)
  
    def verify_data(self,message):
        #get session
        session = self.parent.sessions.get_connection_sessions(message.message["session_id"])
        if not session:
            if self.DEBUG:
                print("Invalid session")
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
        if message.message["message"]["counter"]<session["counter"]:
            if self.parent.DEBUG:
                print("Invalid counter")
            return
        #check signature
        msg_signature = message.message["message"]["data"].pop('signature')
        #stringify the data payload
        msg_data = json.dumps(message.message["message"]["data"])
        #verify the message signature
        if EncryptionModule.verify(msg_data, msg_signature, EncryptionModule.reformat_public_key(session["pk"])) == False:
            if self.parent.DEBUG:
                print("signature not verified")
            return None
        #re-add signature to message
        message.message["message"]["data"]["signature"] = msg_signature
        return message.message

    def send_message(self, target, message):
        
        #define target sessions
        if target == "all":
            node_ids = self.parent.sessions.get_active_nodes()
        else :
            node_ids = [target]
        #iterate over target sessions
        for node_id in node_ids:
            #check if session is available
            if not self.parent.sessions.has_active_connection_session(node_id):
                if self.parent.DEBUG:
                    print("No active session")
                return Response("No active session", status=400)
            #get session
            session = self.parent.sessions.get_connection_session_by_node_id(node_id)
            #sign message
            msg = json.dumps(message)
            msg_signature = EncryptionModule.sign(msg,self.parent.sk)
            #add signature to message
            message["signature"] = msg_signature
            #prepare message data
            msg_data = OrderedDict({
            "timestamp": str(datetime.datetime.now()),
                "counter": self.parent.comm.counter,
                "data":message
                })
            #stringify message data
            msg_data = json.dumps(msg_data)
            #encrypt message data
            encrypted_data = EncryptionModule.encrypt_symmetric(msg_data,session["key"])
            #prepare message payload
            msg_payload = OrderedDict({
                "type": "data_exchange",
                "node_id": self.parent.node_id,
                "node_type": self.parent.node_type,
                "data": msg_data,
                "pos": self.parent.pos,
                "port": self.parent.port,
                "session_id": session["session_id"],
                "message": encrypted_data
                })
            #add message to the queue
            self.parent.queues.put_queue({
                "target": session["node_id"],
                "message": msg_payload,
                "pos": self.parent.pos,
            },"outgoing")