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
        node_id = data["node_id"]
        message = data["message"]
        #check if session is available
        if self.parent.sessions.has_active_connection_session(node_id):
            #get session
            session = self.parent.sessions.get_connection_session_by_node_id(node_id)
            #prepare message data
            msg_data = OrderedDict({
            "timestamp": str(datetime.datetime.now()),
                "counter": self.parent.comm.counter,
                "data":{
                    "message": message
                    }
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
            #stringify message payload
            msg_payload_str = json.dumps(msg_payload)
            #hash and sign message payload
            msg_signature = EncryptionModule.sign(msg_payload_str,self.parent.sk)
            #add signature and hash to message payload
            msg_payload["signature"] = msg_signature
            #add message to the queue
            self.parent.queues.put_queue({
                "target": session["node_id"],
                "message": msg_payload,
                "pos": self.parent.pos,
            },"outgoing")
            return Response("OK", status=200)
    
    @staticmethod
    def listen(self):
        '''
        receive message from the network
        '''
        #receive message from the network and put it in the queue
        self.parent.queues.put_queue(request.json,"incoming")
        return Response("OK", status=200)
  
    def handle_data(self,message):
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
        message_type = "str"
        if type(message.message["message"]["data"]["message"]) == dict:
            message_data= json.dumps(message.message["message"]["data"]["message"])
            message_type = "dict"
        else:
            message_data = message.message["message"]["data"]["message"]
            message_type = "str"
        #print message content
        #if self.parent.DEBUG:
        #    self.server.logger.warning(f'{message.message["node_id"]} : {message_data}')
        #add message to output queue
        self.parent.queues.put_output_queue(message_data,message.message["node_id"],message_type)
      
    '''
    

if __name__ == "__main__":
    #node = NetworkInterface("https://webhook.site/da3aee86-1fff-44c0-8f5f-5eeee42e5bc3",500,None)
    secret = "secret"
    auth = '1234567890'
    port = randint(5000,6000)
    node = NetworkInterface("http://127.0.0.1:5000",port,None,secret,auth,True)
    node.start()
    while True:
        #get message from output queue
        message = node.pop_output_queue()
        if message:
            print(f"Message from {message['node_id']} : {message['message']}")

    '''