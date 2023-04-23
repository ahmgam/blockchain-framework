from network import NetworkInterface
from connector import CommunicationModule
from session import SessionManager
from flask import Flask, request
from encryption import EncryptionModule
from queues import QueueManager
from heartbeat import HeartbeatProtocol
from discovery import DiscoveryProtocol
from threading import Thread
from messages import *
import uuid
from random import randint
class Silsila:
    def __init__(self,node_id,node_type,endpoint,port,secret_key,auth=None,DEBUG=False):
        '''
        Initialize network interface
        '''
        self.DEBUG = DEBUG
        #define secret 
        self.secret_key = secret_key
        #define dummy position
        self.pos = "0,0,0"
        #define node id
        self.node_id = node_id
        #define node type
        self.node_type = node_type
        #get port from parent
        self.endpoint = endpoint
        #define auth
        self.auth = auth
        #define port
        self.port = port
        #check if key pairs is available
        self.pk, self.sk = EncryptionModule.load_keys('pk.pem', 'sk.pem')
        #if not, create new public and private key pair
        if self.pk == None:
            self.pk, self.sk = EncryptionModule.generate_keys()
            EncryptionModule.store_keys('pk.pem', 'sk.pem',self.pk,self.sk)
        #define communication module
        self.comm = CommunicationModule(self)
        #define session manager
        self.sessions = SessionManager()
        #define queue
        self.queues = QueueManager()
        #define network interface
        self.network = NetworkInterface(self)
        #define heartbeat protocol
        self.heartbeat = HeartbeatProtocol(self)
        #define discovery protocol
        self.discovery = DiscoveryProtocol(self)
        #define listening flask
        self.server = Flask(__name__)
        #define heartbeat thread
        self.heartbeat_thread = Thread(target=self.heartbeat.heartbeat)
        self.heartbeat_thread.daemon = True
        
        #define discovery thread
        self.discovery_thread = Thread(target= self.discovery.discovery)
        #self.discovery_thread = threading.Thread(target=lambda: self.discovery(self))
        self.discovery_thread.daemon = True
        #define handler thread
        self.handler_thread = Thread(target=self.handle)
        self.handler_thread.daemon = True
        
    def start(self):
        self.heartbeat_thread.start()
        self.discovery_thread.start()
        self.handler_thread.start()
        #start flask server
        self.network.server.run( port=self.port)
        
    def handle(self):
        '''
        start listening for incoming connections
        '''
        while True:
            #get message from queue
            try:
                message_buffer = self.queues.pop_queue()
                
                if message_buffer:
                    #check message type
                    if str(message_buffer["type"]) == "incoming":
                        message =Message(message_buffer["message"]) 
                        if message.message["node_id"]==self.node_id:
                            continue
                        if message.message["type"].startswith("discovery"):
                            self.discovery.handle(message)
                        elif message.message["type"].startswith("heartbeat"):
                            self.heartbeat.handle(message)
                        #elif message.message["type"].startswith("consensus"):
                        #    self.consensus.handle(message)
                        elif message.message["type"]=="data_exchange":
                            #for test purposes
                            self.network.handle_data(message)
                        else:
                            if self.DEBUG:
                                print(f"unknown message type {message.message['type']}")
                    elif str(message_buffer["type"]) == "outgoing":
                        try:
                            self.comm.send(message_buffer["message"])
                        except Exception as e:
                            if self.DEBUG:
                                print(e)
                    else:
                        if self.DEBUG:
                            print(f'unknown message type {message_buffer["type"]}')
            except Exception as e:
                if self.DEBUG:
                    print(f"error in handling message: {e}")
                continue
          
if __name__ == "__main__":         
    secret = "secret"
    auth = '1234567890'
    port = randint(5001,6000)
    node_id = str(uuid.uuid4())
    node_type = "uav"
    node = Silsila(node_id,node_type,"http://127.0.0.1:5000",port,secret,auth,True)
    node.start()
    while True:
        #get message from output queue
        message = node.queues.pop_output_queue()
        if message:
            node.network.server.logger.warning(f"Message from {message['source']} : {message['message']}")
            