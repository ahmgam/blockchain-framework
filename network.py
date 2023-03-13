import requests
from flask import Flask, Response,request
from messages import *
import threading
from time import sleep
import uuid
import datetime
import rsa
import os

class CommunicationModule:
    def __init__(self,endpoint):
        self.endpoint = endpoint

    def send(self, message):
    
        req =   requests.post(self.endpoint+'/',
                            json = message,
                            headers = {'Content-Type': 'application/json'})
        if req.status_code == 200:
            return True
        else :
            return False
    
            
            
class NetworkInterface:
    
    def __init__(self,endpoint,port,parent):
        '''
        Initialize network interface
        '''
        #define dummy position
        self.pos = "0,0,0"
        #define node id
        self.node_id = uuid.uuid4().hex
        #define node type
        self.node_type = "uav"
        #define counter
        self.counter = 0
        #define parent
        self.parent = parent
        #get port from parent
        self.endpoint = endpoint
        #define communication module
        self.comm = CommunicationModule(self.endpoint)
        #define port
        self.port = port
        #define discovery interval
        self.discovery_interval = 10
        #check if key pairs is available
        self.pk, self.sk = self.load_keys()
        #if not, create new public and private key pair
        if self.pk == None:
            self.pk, self.sk = self.generate_keys()
            self.store_keys('pk.pem', 'sk.pem')
        #define session manager
        self.discovery_sessions = []
        self.connection_sessions = []
        
        #define listening flask
        self.server = Flask(__name__)
        self.server.add_url_rule('/', 'listen',lambda : self.listen(self), methods=['POST'])
        #self.server.add_url_rule('/', 'listen',self.listen, methods=['POST'])

        #define heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self.heartbeat, args=(self.comm,))
        self.heartbeat_thread.daemon = True
        
        #define discovery thread
        self.discovery_thread = threading.Thread(target= self.discovery, args=(self.comm,))
        #self.discovery_thread = threading.Thread(target=lambda: self.discovery(self))

        self.discovery_thread.daemon = True
        
           
    
    def start(self):
        self.heartbeat_thread.start()
        self.discovery_thread.start()
        #start flask server
        self.server.run( port=self.port)
        
    #@staticmethod 
    def send(self,endpoint,message):
        '''
        Send message to the given public key
        '''
        print("sending message")
        req = requests.post(f"{endpoint}", json=message)
        print(req.status_code)
        if req.status_code == 200:
            return True
        else:
            return False
        #send message to the network
    @staticmethod
    def listen(self):
        '''
        receive message from the network
        '''
        message =Message(request.json) 
        if message.message["type"] == "discovery":
            self.respond_to_discovery(message)
        elif message.message["type"] == "discovery_response":
            self.verify_discovery(message)
        elif message.message["type"] == "discovery_verification":
            self.verify_discovery_response(message)
        elif message.message["type"] == "discovery_verification_response":
            self.approve_discovery(message)
        elif message.message["type"] == "discovery_approval":
            self.approve_discovery_response(message)
        elif message.message["type"] == "discovery_approval_response":
            self.add_node(message)
        elif message.message["type"] == "heartbeat":
            self.handle_heartbeat(message)
        elif message.message["type"] == "heartbeat_response":
            self.handle_heartbeat_response(message)
        elif message.message["type"] == "data":
            self.handle_data(message)
        else:
            print("unknown message type")
        
        #receive message from the network
        
    
    def handle(self):
        '''
        start listening for incoming connections
        '''
        while True:
            pass
        #listen for incoming connections
        
    def discovery(self,comm):
        '''
        publish message to the network
        '''
        #broadcast message to the network
        while True:
            print("sending discovery message")
            self.discover()               
            sleep(self.discovery_interval)
        
    def heartbeat(self):
        '''
        send heartbeat to all nodes
        '''
        pass
        #send heartbeat to all nodes
        
    ################################
    # key management
    ################################    
    def generate_keys(self):
        '''
        generate new public and private key pair
        '''
        
        #generate new public and private key pair
        pk, sk=rsa.newkeys(2048)
        return pk, sk
    
    def store_keys(self,public_key_file,private_key_file):
        '''
        store public and private key pair in file
        '''
        
        #store public and private key pair in file
        # Save the public key to a file
        with open(public_key_file, 'wb') as f:
            f.write(self.pk.save_pkcs1())

        # Save the private key to a file
        with open(private_key_file, 'wb') as f:
            f.write(self.sk.save_pkcs1())
        return None
    
    def load_keys(self):
        '''
        load public and private key pair from file
        '''
        #check if key pairs is available
        if os.path.isfile('pk.pem') and os.path.isfile('sk.pem'):
            #load public and private key pair from file
            with open('pk.pem', 'rb') as f:
                pk = rsa.PublicKey.load_pkcs1(f.read())
            with open('sk.pem', 'rb') as f:
                sk = rsa.PrivateKey.load_pkcs1(f.read())
            return pk, sk
        else:        
            return None, None
        
    def sign(self,message):
        if self.sk == None:
            return None
        else :
            return self.sk.sign(json.dumps(message).encode("utf-8"))
        
    def verify(self,message,signature):
        if self.pk == None:
            return None
        else:
            return self.pk.verify(json.dumps(message).encode("utf-8"), signature)
        
    def hash(self,message):
        return sha256(json.dumps(message).encode("utf-8")).hexdigest()
    
    ################################
    # discovery protocol
    ################################
    def discover(self):
        pass
        #discover new nodes on the network
        
        payload = {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "pos": self.pos,
            "type": "discovery_response",
            "port": self.port,
            "session_id": "",
            "message":{
                "timestamp": str(datetime.datetime.now()),
                "counter": self.counter,
                "data":{
                    "pk": str(self.pk)
                    }
                }
            }
        print(payload)
        message = DiscoveryMessage(payload)
        message.message['hash'] = message.get_hash()
        #message.sign(self.sk)
        try:
            self.comm.send({"target": "all",
                    "message": message.to_dict(),
                    "pos": self.pos})
        except Exception as e:
            print(e)
        
    def respond_to_discovery(self,message):
        pass
        #respond to discovery requests and send challenge
        
    def verify_discovery(self,message):
        pass
        #verify discovery request and send challenge response
        
    def verify_discovery_response(self,message):
        pass
        #verify discovery response and add node to the network
    
    def approve_discovery(self,message):
        pass
        #approve discovery request and send approval response
    def approve_discovery_response(self,message):
        pass
        #approve discovery response and add node to the network
    
    def get_nodes(self):
        pass
        #get all nodes on the network    
 
    ################################
    # session management
    ################################       
    def create_session(self, pk,type):
        pass
        #create new session with the given public key and type
    
    def end_session(self, pk):
        pass
        #end session with the given public key
        
    def get_session(self, pk):
        pass
        #get session with the given public key
        
    def get_sessions(self):
        pass
        #get all sessions   
             
    ################################
    # connection management
    ################################
    def connect(self, ip):
        pass
        #connect to the given ip

    def disconnect(self, ip):
        pass
        #disconnect from the given ip
    def send(self, ip, message):
        pass
        #send message to the given public key
        
    def broadcast(self, message):
        pass
        #broadcast message to the network
        
    def receive(self):
        pass
        #receive message from the network
        
    def listen(self):
        pass
        #listen for incoming connections
        
    def encrypt(self, message):
        pass
        #encrypt message
        
    def decrypt(self, message):
        pass
        #decrypt message
        
    ################################
    # queue management
    ################################
    def add_to_send_queue(self, ip, message):
        pass
        #add message to send queue
        
    def add_to_receive_queue(self, ip, message):
        pass
        #add message to receive queue
        
    def get_from_send_queue(self):
        pass
        #get message from send queue
    
    def get_from_receive_queue(self):
        pass
        #get message from receive queue
    
    
    ################################
    # Heartbeat management
    ################################
    
    def send_heartbeat(self):
        pass
        #send heartbeat to all nodes
    
    def receive_heartbeat(self):
        pass
        #receive heartbeat from all nodes

if __name__ == "__main__":
    #node = NetworkInterface("https://webhook.site/da3aee86-1fff-44c0-8f5f-5eeee42e5bc3",500,None)
    node = NetworkInterface("http://127.0.0.1:5000",500,None)
    node.start()