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
            "message":message,
            "source":self.parent.node_id
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
        
        return message.message

    def send_message(self, target, message):
        
        #define target sessions
        if target == "all":
            node_ids = self.parent.sessions.get_active_nodes()
        elif type(target) == list:
            node_ids = target
        else:
            node_ids = [target]
        #iterate over target sessions
        for node_id in node_ids:
            #check if node_id is local node_id 
            if node_id == self.parent.node_id:
                continue
            #check if session is available
            if not self.parent.sessions.has_active_connection_session(node_id):
                if self.parent.DEBUG:
                    print("No active session")
                return Response("No active session", status=400)
            #get session
            session = self.parent.sessions.get_connection_session_by_node_id(node_id)
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