from network import NetworkInterface
from connector import HTTPCommunicaionModule
from session import SessionManager
from flask import Flask, request
from encryption import EncryptionModule
from queues import QueueManager
from heartbeat import HeartbeatProtocol
from discovery import DiscoveryProtocol
from threading import Thread
from messages import *
from consensus import SBFT
from blockchain import Blockchain
import sys
from time import sleep
from random import randint
class Silsila:
    def __init__(self,node_id,node_type,endpoint,port,secret_key,auth=None,DEBUG=False):
        '''
        Initialize network interface
        '''
        #define debug mode
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
        self.comm = HTTPCommunicaionModule(self.node_id,self.endpoint,self.port,self.auth,self.DEBUG)
        #define session manager
        self.sessions = SessionManager(self)
        #define queue
        self.queues = QueueManager()
        #define network interface
        self.network = NetworkInterface(self)
        #define heartbeat protocol
        self.heartbeat = HeartbeatProtocol(self)
        #define discovery protocol
        self.discovery = DiscoveryProtocol(self)
        #define blockchain
        self.blockchain = Blockchain(self)
        #define consensus protocol
        self.consensus = SBFT(self)
        #cron interval
        self.cron_interval = 1
        #cron procedure list
        self.cron_procedures = []
        #define cron thread
        self.cron_thread = Thread(target= self.cron)
        #self.discovery_thread = threading.Thread(target=lambda: self.discovery(self))
        self.cron_thread.daemon = True
        #define handler thread
        self.handler_thread = Thread(target=self.handle)
        self.handler_thread.daemon = True
        
    def start(self):
        #regiser cron procedures
        self.cron_procedures.append(self.heartbeat.cron)
        self.cron_procedures.append(self.discovery.cron)
        self.cron_procedures.append(self.consensus.cron)
        self.cron_procedures.append(self.blockchain.cron)
        #start cron thread
        self.cron_thread.start()
        #start handler thread
        self.handler_thread.start()
        #start flask server
        self.comm.start()
     
    def cron(self):
        while True:
            for procedure in self.cron_procedures:
                procedure()
            sleep(self.cron_interval)
            
    def handle(self):
        '''
        start listening for incoming connections
        '''
        while True:
            #check if there is any message in comm buffer
            while self.comm.is_available():
                comm_buffer =self.comm.get()
                self.queues.put_queue(comm_buffer["message"],comm_buffer["type"])
            #get message from queue
            try:
                message_buffer = self.queues.pop_queue()
                
                if message_buffer:
                    #check message type
                    if str(message_buffer["type"]) == "incoming":
                        message =Message(message_buffer["message"]) 
                        if message.message["node_id"]==self.node_id:
                            continue
                        elif message.message["type"].startswith("discovery"):
                            self.discovery.handle(message)
                        elif message.message["type"].startswith("heartbeat"):
                            self.heartbeat.handle(message)
                        elif message.message["type"]=="data_exchange":
                            #for test purposes
                            data = self.network.verify_data(message)
                            if data:
                                pass
                                #self.network.server.logger.warning(f"Message from {data['node_id']} : {data['message']}")
                                self.consensus.handle(data)
                        else:
                            if self.DEBUG:
                                print(f"unknown message type {message.message['type']}")
                    elif str(message_buffer["type"]) == "outgoing":
                        try:
                            self.comm.send(message_buffer["message"])
                        except Exception as e:
                            if self.DEBUG:
                                print(e)
                    elif str(message_buffer["type"]) == "consensus":
                        self.consensus.send(message_buffer['message'])
                    else:
                        if self.DEBUG:
                            print(f'unknown message type {message_buffer["type"]}')
            except Exception as e:
                if self.DEBUG:
                    print(f"error in handling message: {e}")
                continue
            #check if there is any message in output queue
            output_buffer = self.queues.pop_output_queue()
            if output_buffer:
                try:
                    self.blockchain.add_transaction(output_buffer["message"]["table"],output_buffer["message"]["data"])
                except Exception as e:
                    if self.DEBUG:
                        print(e)
                
             

if __name__ == "__main__":         
    secret = "secret"
    auth = '1234567890'
    if len(sys.argv) > 1:
        port = 5000+ int(sys.argv[1])
        node_id = str(sys.argv[1])
        node_type = "uav"
    else:
        port = 5002
        node_id = "2"
        node_type = "uav"
    node = Silsila(node_id,node_type,"http://127.0.0.1:5000",port,secret,auth,True)
    target_id = 0
    self_port = 1
    node.start()
    while True:
        #pop message from output queue
        msg = node.queues.pop_output_queue()
        if msg:
            node.comm.server.logger.warning(f'{msg["source"]} : {msg["message"]}')
    
            