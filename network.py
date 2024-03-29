import requests
from flask import Flask, Response,request
from messages import *
import threading
from time import sleep,mktime
import uuid
import datetime
import rsa
import os
import queue
from cryptography.fernet import Fernet
from random import choices, randint
from string import ascii_lowercase, digits, ascii_uppercase
from base64 import  b64encode, b64decode
from math import ceil

class CommunicationModule:
    def __init__(self,endpoint,auth=None,timeout=5,DEBUG=False):
        self.endpoint = endpoint
        self.auth = auth
        self.timeout = timeout
        self.counter = 0
        self.DEBUG = DEBUG
    def send(self, message):
        if self.DEBUG:
            print(f'{datetime.datetime.now()} : Sending message to {message["target"]} with type {message["message"]["type"]} and content {message["message"]["hash"]}')
        headers = {'Content-Type': 'application/json'}
        if self.auth != None:
            headers['Authorization'] = self.auth
        try:
            req =   requests.post(self.endpoint+'/',
                                json = message,
                                headers = headers,timeout=self.timeout)
        except Exception as e:
            if self.DEBUG:
                print(f"Error sending message: {e}")
            return False
        if req.status_code == 200:
            self.counter += 1
            return True
        else :
            if self.DEBUG:
                print(f"Error sending message: {req.status_code}")
            return False
    
            
            
class NetworkInterface:
    
    def __init__(self,endpoint,port,parent,secret_key,auth=None,DEBUG=False):
        '''
        Initialize network interface
        '''
        self.DEBUG = DEBUG
        #define secret 
        self.secret_key = secret_key
        #define dummy position
        self.pos = "0,0,0"
        #define node id
        self.node_id = uuid.uuid4().hex
        #define node type
        self.node_type = "uav"
        #define parent
        self.parent = parent
        #get port from parent
        self.endpoint = endpoint
        #define communication module
        self.comm = CommunicationModule(self.endpoint,auth)
        #define port
        self.port = port
        #define discovery interval
        self.discovery_interval = 10
        #define heartbeat interval
        self.heartbeat_interval = 5
        #check if key pairs is available
        self.pk, self.sk = self.load_keys()
        #if not, create new public and private key pair
        if self.pk == None:
            self.pk, self.sk = self.generate_keys()
            self.store_keys('pk.pem', 'sk.pem')
        #define session manager
        self.discovery_sessions = {}
        self.connection_sessions = {}
        #define queue
        self.queue = queue.Queue()
        #define listening flask
        self.server = Flask(__name__)
        #disable logging if not in debug mode
        if not self.DEBUG:
            self.server.logger.disabled = True
        self.server.add_url_rule('/', 'listen',lambda : self.listen(self), methods=['POST'])
        #add message send endpoint
        self.server.add_url_rule('/send', 'send',lambda : self.send(self), methods=['POST'])
        #self.server.add_url_rule('/', 'listen',self.listen, methods=['POST'])

        #define heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self.heartbeat)
        self.heartbeat_thread.daemon = True
        
        #define discovery thread
        self.discovery_thread = threading.Thread(target= self.discovery, args=(self.comm,))
        #self.discovery_thread = threading.Thread(target=lambda: self.discovery(self))
        self.discovery_thread.daemon = True
        #define handler thread
        self.handler_thread = threading.Thread(target=self.handle)
        self.handler_thread.daemon = True
        
    def start(self):
        self.heartbeat_thread.start()
        self.discovery_thread.start()
        self.handler_thread.start()
        #start flask server
        self.server.run( port=self.port)
        
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
        if self.has_active_connection_session(node_id):
            #get session
            session = self.get_connection_session_by_node_id(node_id)
            #prepare message data
            msg_data = OrderedDict({
            "timestamp": str(datetime.datetime.now()),
                "counter": self.comm.counter,
                "data":{
                    "message": message
                    }
                })
            #stringify message data
            msg_data = json.dumps(msg_data)
            #encrypt message data
            encrypted_data = self.encrypt_symmetric(msg_data,session["key"])
            #prepare message payload
            msg_payload = OrderedDict({
                "type": "data_exchange",
                "node_id": self.node_id,
                "node_type": self.node_type,
                "data": msg_data,
                "pos": self.pos,
                "port": self.port,
                "session_id": session["session_id"],
                "message": encrypted_data
                })
            #stringify message payload
            msg_payload_str = json.dumps(msg_payload)
            #hash and sign message payload
            msg_hash,msg_signature = self.hash_and_sign(msg_payload_str)
            #add signature and hash to message payload
            msg_payload["signature"] = msg_signature
            msg_payload["hash"] = msg_hash
            #add message to the queue
            self.queue.put({"type":"outgoing","message":{
                "target": session["node_id"],
                "message": msg_payload,
                "pos": self.pos,
            }},"outgoing")
            return Response("OK", status=200)
    @staticmethod
    def listen(self):
        '''
        receive message from the network
        '''
        #receive message from the network and put it in the queue
        self.queue.put({"type":"incoming","message":request.json })
        return Response("OK", status=200)
        
    def handle(self):
        '''
        start listening for incoming connections
        '''
        while True:
            #get message from queue
            try:
                message_buffer = self.pop_queue()
                
                if message_buffer:
                    #check message type
                    if str(message_buffer["type"]) == "incoming":
                        message =Message(message_buffer["message"]) 
                        if message.message["node_id"]==self.node_id:
                            continue
                        
                        if message.message["type"] == "discovery":
                            if self.DEBUG:
                                print(f"Received message from {message.message['node_id']} of type {message.message['type']}, starting response_to_discovery")
                            self.respond_to_discovery(message)
                        elif message.message["type"] == "discovery_response":
                            if self.DEBUG:
                                print(f"Received message from {message.message['node_id']} of type {message.message['type']}, starting verify_discovery")
                            self.verify_discovery(message)
                        elif message.message["type"] == "discovery_verification":
                            if self.DEBUG:
                                print(f"Received message from {message.message['node_id']} of type {message.message['type']}, starting verify_discovery_response")
                            self.verify_discovery_response(message)
                        elif message.message["type"] == "discovery_verification_response":
                            if self.DEBUG:
                                print(f"Received message from {message.message['node_id']} of type {message.message['type']}, starting approve_discovery")
                            self.approve_discovery(message)
                        elif message.message["type"] == "discovery_approval":
                            if self.DEBUG:
                                print(f"Received message from {message.message['node_id']} of type {message.message['type']}, starting approve_discovery_response")
                            self.approve_discovery_response(message)
                        elif message.message["type"] == "discovery_approval_response":
                            if self.DEBUG:
                                print(f"Received message from {message.message['node_id']} of type {message.message['type']}, starting finalize_discovery")
                            self.finalize_discovery(message)
                        elif message.message["type"] == "heartbeat":
                            if self.DEBUG:
                                print(f"Received message from {message.message['node_id']} of type {message.message['type']}, starting handle_heartbeat")
                            self.handle_heartbeat(message)
                        elif message.message["type"] == "heartbeat_response":
                            if self.DEBUG:
                                print(f"Received message from {message.message['node_id']} of type {message.message['type']}, starting handle_heartbeat_response")
                            self.handle_heartbeat_response(message)
                        elif message.message["type"] == "data_exchange":
                            if self.DEBUG:
                                print(f"Received message from {message.message['node_id']} of type {message.message['type']}, starting handle_data")
                            self.handle_data(message)
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
           
        #listen for incoming connections
        
    def discovery(self,comm):
        '''
        publish message to the network
        '''
        #broadcast message to the network
        while True:
            sleep(self.discovery_interval)
            self.discover()
            
    def heartbeat(self):
        '''
        send heartbeat to all nodes
        '''
        pass
        #send heartbeat to all nodes
        while True:
            for session_id, session in self.connection_sessions.items():
                #check if time interval is passed
                session_time = mktime(datetime.datetime.now().timetuple()) - session["last_heartbeat"]
                if session_time > self.heartbeat_interval and session["status"] == "active":
                    #send heartbeat
                    self.send_heartbeat(session)
                    #update last heartbeat time
                    self.connection_sessions[session_id]["last_heartbeat"] = mktime(datetime.datetime.now().timetuple())
                    sleep(1)
        
    ################################
    # key management
    ################################    
    def format_bytes(self,b):
        return bytes(b64encode(b)).decode('utf-8')
    
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
            return rsa.sign(json.dumps(message).encode("utf-8"), self.sk, 'SHA-256')
            #return self.sk.sign(json.dumps(message).encode("utf-8"))
        
    def verify(self,message,signature,pk):
        #define public key instance from string
        pk = rsa.PublicKey.load_pkcs1(pk)
        #verify signature
        return pk.verify(json.dumps(message).encode("utf-8"), signature)
        
    def hash(self,message):
        return sha256(json.dumps(message).encode("utf-8")).hexdigest()
    
    def hash_and_sign(self,message):
        hash = rsa.compute_hash(message.encode("latin-1"), 'SHA-1')
        signature = rsa.sign_hash(hash, self.sk, 'SHA-1')
        return self.format_bytes(hash) , self.format_bytes(signature)
    
    def generate_challenge(self, length=20):
        return ''.join(choices(ascii_lowercase, k=length))
    
    def solve_challenge(self,challenge):
        solution = self.hash(challenge+self.secret_key)
        client_sol = solution[0:len(solution)//2]
        server_sol = solution[len(solution)//2:]
        return client_sol, server_sol
    
    def format_public_key(self,pk):
        #remove new line characters
        pk = str(pk.save_pkcs1().decode('ascii'))
        pk = pk.replace('\n-----END RSA PUBLIC KEY-----\n', '').replace('-----BEGIN RSA PUBLIC KEY-----\n','')
        return pk
        
    def reformat_public_key(self,pk):
        return f"-----BEGIN RSA PUBLIC KEY-----\n{str(pk)}\n-----END RSA PUBLIC KEY-----\n"
        
    def generate_symmetric_key(self):
        return Fernet.generate_key().decode("ascii")
         
    def encrypt(self, message, pk=None):
        if pk == None:
            pk = self.pk
        if type(pk) == str:
            pk = rsa.PublicKey.load_pkcs1(pk)
        #encrypt message
        result = []
        for i in range (ceil(len(message)/245)):
            start_index = i*245
            end_index = (i+1)*245 if (i+1)*245 < len(message) else len(message)
            result.append(rsa.encrypt(message[start_index:end_index].encode("ascii"), pk))   
        return b64encode(b''.join(result)).decode('utf-8')
    
    def decrypt(self, message):
        #decrypt message
        message = b64decode(message.encode('utf-8'))
        try:
            result = []
            for i in range (ceil(len(message)/256)):
                start_index = i*256
                end_index = (i+1)*256 if (i+1)*256 < len(message) else len(message)
                result.append(rsa.decrypt(message[start_index:end_index], self.sk).decode("ascii"))   
            return ''.join(result)
        except Exception as e:
            print(f"error decrypting message: {e}")
            return None
    
    def encrypt_symmetric(self,message,key):
        f = Fernet(key.encode("ascii"))
        return b64encode(f.encrypt(message.encode("utf-8"))).decode('utf-8')
    
    def decrypt_symmetric(self,ciphertext,key):
        f = Fernet(key.encode("ascii"))
        return f.decrypt(b64decode(ciphertext.encode('utf-8'))).decode("ascii")
    
    ################################
    # discovery protocol
    ################################
    def discover(self):
        #discover new nodes on the networن       
        #define message payload
        
        payload = OrderedDict({
            "node_id": self.node_id,
            "node_type": self.node_type,
            "pos": self.pos,
            "type": "discovery",
            "port": self.port,
            "session_id": "",
            "message":{
            "timestamp": str(datetime.datetime.now()),
                "counter": self.comm.counter,
                "data":{
                    "pk": self.format_public_key(self.pk),
                    }
                },
            })
        #stringify the data payload
        msg_data = json.dumps(payload,ensure_ascii=False)
        #generate hash and signature
        msg_hash,msg_signature = self.hash_and_sign(msg_data)
        #add hash and signature to the payload
        payload["hash"] = str(msg_hash)
        payload["signature"] = str(msg_signature)
        #create message object
        message = DiscoveryMessage(payload)
        self.put_queue({"target": "all",
                "message": message.message,
                "pos": self.pos}, "outgoing")
        
    def respond_to_discovery(self,message):
        #respond to discovery requests and send challenge
        #first verify the message
        try:
            message = DiscoveryMessage(message.message) 
        except Exception as e:
            if self.DEBUG:
                print(f"validation error {e}")
            return None
        #verify the message hash 
        buff = message.message
        msg_hash = buff.pop('hash')
        msg_signature = buff.pop('signature')
        msg_pk =self.reformat_public_key(buff["message"]["data"]["pk"])
        #stringify the data payload
        msg_data = json.dumps(buff)
        hash,signature = self.hash_and_sign(msg_data)
        if hash != msg_hash:
            if self.DEBUG:
                print("hash not verified")
            return None
        #verify the message signature
        if signature!=msg_signature:
            if self.DEBUG:
                print("signature not verified")
            return None
        #check if the node is already connected to the network
        if self.has_active_connection_session(message.message["node_id"]):
            if self.DEBUG:
                print("connection session is already active") 
            return None
        #check if the node has active discovery session with the sender
        if self.get_discovery_session(message.message["node_id"]):
            if self.DEBUG:    
                print("discovery session is already active")
            return None
        else:
            #create new session
            session_data = {
                "pk": buff["message"]["data"]["pk"],
                "role":"server",
                "counter": message.message["message"]["counter"],
                "node_type": message.message["node_type"],     
            }
            self.create_discovery_session(message.message["node_id"],session_data)
        #prepare discovery response message
        msg_data =OrderedDict( {
                "timestamp": str(datetime.datetime.now()),
                "counter": self.comm.counter,
                "data":{
                    "pk": self.format_public_key(self.pk)
                    }
                })
        #stringify the message
        msg_data = json.dumps(msg_data)
        
        #encrypt the message
        data_encrypted = self.encrypt(msg_data,msg_pk)   
        payload = {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "pos": self.pos,
            "type": "discovery_response",
            "port": self.port,
            "session_id": "",
            "message": data_encrypted
            }
        #stringify the message
        payload_data = json.dumps(payload)
        #get message hash,signature
        data_hash,data_signature = self.hash_and_sign(payload_data)
        #add hash and signature to the message
        payload["hash"] = data_hash
        payload["signature"] = data_signature
        #send the message
        self.put_queue({"target": message.message["node_id"],
                    "message": payload,
                    "pos": self.pos}, "outgoing")
    
    def verify_discovery(self,message):
        #verify discovery request and send challenge response
        #check if the node is already connected to the network
        if self.has_active_connection_session(message.message["node_id"]):
            if self.DEBUG:    
                print("connection session is already active")
            return None
        #verify the message hash 
        buff = message.message
        msg_hash = buff.pop('hash')
        msg_signature = buff.pop('signature')
        msg_data=json.dumps(buff)
        #verify the message hash and signature
        hash , signature = self.hash_and_sign(msg_data)
        if hash != msg_hash:
            if self.DEBUG:
                print("hash not verified")
            return None
        #verify the message signature
        if signature!=msg_signature:
            if self.DEBUG:    
                print("signature not verified")
            return None
        #decrypt the message
        try:
            decrypted_data = self.decrypt(message.message["message"])
            
        except Exception as e:
            if self.DEBUG:    
                print(f"error decrypting and parsing data : {e}")
            return None
        #parse the message
        decrypted_data = json.loads(decrypted_data)
        #validate the message
        message.message["message"] = decrypted_data
        try :
            message=DiscoveryResponseMessage(message.message)
        except Exception as e:
            if self.DEBUG:
                print(f"error validating message : {e}")
            return None
        #generate challenge random string
        challenge = self.generate_challenge()
        #solve the challenge
        client_sol, server_sol = self.solve_challenge(challenge)
        #create discovery session
        session_data = {
            "pk": decrypted_data["data"]["pk"],
            "role": "client",
            "counter": message.message["message"]["counter"],
            "node_type": message.message["node_type"],
            "challenge": challenge,
            "client_challenge_response": client_sol,
            "server_challenge_response": server_sol
        }
        #create discovery session
        self.create_discovery_session(message.message["node_id"],session_data)
        #prepare verification message 
        msg_data = OrderedDict({
                "timestamp": str(datetime.datetime.now()),
                "counter": self.comm.counter,
                "data":{
                    "challenge": challenge,
                    "client_challenge_response": client_sol
                    }
                })
        #stringify the message
        msg_data = json.dumps(msg_data)
        
        #encrypt the message
        data_encrypted = self.encrypt(msg_data,self.reformat_public_key(decrypted_data["data"]["pk"]))
        payload = OrderedDict({
            "node_id": self.node_id,
            "node_type": self.node_type,
            "pos": self.pos,
            "type": "discovery_verification",
            "port": self.port,
            "session_id": "",
            "message": data_encrypted
            })
        #stringify the payload
        payload_data = json.dumps(payload)
        #get message hash and signature
        data_hash,data_signature = self.hash_and_sign(payload_data)
        #add hash and signature to the message
        payload["hash"] = data_hash
        payload["signature"] = data_signature
        #send the message
        self.put_queue({"target": message.message["node_id"],
                    "message": payload,
                    "pos": self.pos},"outgoing")
 
    def verify_discovery_response(self,message):
        #verify discovery response and add node to the network
        #check if the node is already connected to the network
        if self.has_active_connection_session(message.message["node_id"]):
            if self.DEBUG:
                print("connection session is already active")
            return None
        #check if the node does not have active discovery session with the sender
        session = self.get_discovery_session(message.message["node_id"])
        if not session:
            if self.DEBUG:
                print("node does not have active discovery session with the sender")
            return None
        
        #verify the message hash 
        buff = message.message
        msg_hash = buff.pop('hash')
        msg_signature = buff.pop('signature')
        #verify the message hash
        msg_data = json.dumps(buff)
        #verify the message hash and signature
        hash , signature = self.hash_and_sign(msg_data)
        if hash != msg_hash:
            if self.DEBUG:
                print("hash not verified")
            return None
        if signature!=msg_signature:
            if self.DEBUG:
                print("signature not verified")
            return None
        #get the public key of the sender from the session
        pk = session["pk"]
        #decrypt the message
        try:
            decrypted_data = self.decrypt(message.message["message"])
            
        except Exception as e:
            if self.DEBUG:
                print(f"error decrypting and parsing data : {e}")
            return None
        
        #parse the message
        decrypted_data = json.loads(decrypted_data)
        #check if the message counter is valid
        if decrypted_data["counter"] <= session["counter"]:
            if self.DEBUG:
                print("counter not valid")
            return None
        
        #validate the message
        message.message["message"] = decrypted_data
        try :
            message=VerificationMessage(message.message)
        except Exception as e:
            if self.DEBUG:
                print(f"error validating message : {e}")
            return None
        
        #get the challenge from the incoming message
        challenge = decrypted_data["data"]["challenge"]
        #solve the challenge
        client_sol, server_sol = self.solve_challenge(challenge)
        #compare the client challenge response
        if decrypted_data["data"]["client_challenge_response"] != client_sol:
            if self.DEBUG:
                print("client challenge response not verified")
            return None
        #update discovery session
        session_data = {
            "pk": pk,
            "role": "server",
            "counter": message.message["message"]["counter"],
            "node_type": message.message["node_type"],
            "challenge": challenge,
            "client_challenge_response": client_sol,
            "server_challenge_response": server_sol
        }
        #update discovery session
        self.update_discovery_session(message.message["node_id"],session_data)
        #prepare verification message
        msg_data = OrderedDict({
                "timestamp": str(datetime.datetime.now()),
                "counter": self.comm.counter,
                "data":{
                    "challenge": challenge,
                    "server_challenge_response": server_sol
                    }
                })
        #stringify the message
        msg_data = json.dumps(msg_data)
        #encrypt the message    
        data_encrypted = self.encrypt(msg_data,self.reformat_public_key(pk))
        payload = OrderedDict({
            "node_id": self.node_id,
            "node_type": self.node_type,
            "pos": self.pos,
            "type": "discovery_verification_response",
            "port": self.port,
            "session_id": "",
            "message": data_encrypted
            })
        #stringify the payload
        payload_data = json.dumps(payload)
        #get message hash and signature
        data_hash,data_signature  = self.hash_and_sign(payload_data)
        #add hash and signature to the message
        payload["hash"] = data_hash
        payload["signature"] = data_signature
        #send the message
        self.put_queue({"target": message.message["node_id"],
                    "message": payload,
                    "pos": self.pos},"outgoing")

    def approve_discovery(self,message):
        #approve discovery request and send approval response
        #check if the node is already connected to the network
        if self.has_active_connection_session(message.message["node_id"]):
            if self.DEBUG:
                print("connection session is already active")
            return None
        #check if the node does not have active discovery session with the sender
        session = self.get_discovery_session(message.message["node_id"])
        if not session:
            if self.DEBUG:
                print("node does not have active discovery session with the sender")
            return None
        #get the public key of the sender from the session
        pk = session["pk"]
        #verify the message hash 
        buff = message.message
        msg_hash = buff.pop('hash')
        msg_signature = buff.pop('signature')
        #verify the message hash
        msg_data = json.dumps(buff)
        #decrypt the message
        try:
            decrypted_data = self.decrypt(message.message["message"])
            
        except Exception as e:
            if self.DEBUG:
                print(f"error decrypting and parsing data : {e}")
            return None
        #get hash and signature
        hash , signature = self.hash_and_sign(msg_data)
        #verify the message hash
        if hash != msg_hash:
            if self.DEBUG:
                print("hash not verified")
            return None
        #verify the message signature
        if signature!=msg_signature:
            if self.DEBUG:
                print("signature not verified")
            return None
        #parse the message
        decrypted_data = json.loads(decrypted_data)
        #check if the message counter is valid
        if decrypted_data["counter"] <= session["counter"]:
            if self.DEBUG:
                print("counter not valid")
            return None
        
        #validate the message
        message.message["message"] = decrypted_data
        try :
            message=VerificationResponseMessage(message.message)
        except Exception as e:
            if self.DEBUG:
                print(f"error validating message : {e}")
            return None
        #compare the client challenge response
        if decrypted_data["data"]["server_challenge_response"] != session["server_challenge_response"]:
            if self.DEBUG:
                print("client challenge response not verified")
            return None
        
        #creating new session with symmetric key and session id
        #first generate symmetric key
        key = self.generate_symmetric_key()
        #get the session id
        session_id = self.generate_session_id()
        #create new session
        session_data = {
            "pk": pk,
            "node_id": message.message["node_id"],
            "node_type": message.message["node_type"],
            "last_active": mktime(datetime.datetime.now().timetuple()),
            "port": message.message["port"],
            "role": "server",   
            "counter": message.message["message"]["counter"],
            "session_id": session_id,
            "key": key,
            "status": "pending",
            "last_heartbeat": mktime(datetime.datetime.now().timetuple()),
            "approved": False
        }
        self.create_connection_session(session_id,session_data)
        #prepare approval message
        msg_data = OrderedDict({
                "timestamp": str(datetime.datetime.now()),
                "counter": self.comm.counter,
                "data":{
                    "session_id": session_id,
                    "session_key": key,
                    "test_message": self.encrypt_symmetric("client_test",key)
                    }
                })
        #stringify the message
        msg_data = json.dumps(msg_data)
        #get message hash and signature
        data_hash,data_signature  = self.hash_and_sign(msg_data)
        #encrypt the message    
        data_encrypted = self.encrypt(msg_data,self.reformat_public_key(pk))
        payload = OrderedDict({
            "node_id": self.node_id,
            "node_type": self.node_type,
            "pos": self.pos,
            "type": "discovery_approval",
            "port": self.port,
            "session_id": "",
            "message": data_encrypted
            })
        #stringify the payload
        payload_data = json.dumps(payload)
        #get message hash 
        data_hash,data_signature = self.hash_and_sign(payload_data)
        #add hash and signature to the message
        payload["hash"] = data_hash
        payload["signature"] = data_signature
        #send the message
        self.put_queue({"target": message.message["node_id"],
                    "message": payload,
                    "pos": self.pos},"outgoing")
            
    def approve_discovery_response(self,message):
        #approve discovery response and add node to the network
        #check if the node is already connected to the network
        if self.has_active_connection_session(message.message["node_id"]):
            if self.DEBUG:
                print("connection session is already active")
            return None
        #check if the node does not have active discovery session with the sender
        session = self.get_discovery_session(message.message["node_id"])
        if not session:
            if self.DEBUG:
                print("node does not have active discovery session with the sender")
            return None
        #get the public key of the sender from the session
        pk = session["pk"]
        #verify the message hash 
        buff = message.message
        msg_hash = buff.pop('hash')
        msg_signature = buff.pop('signature')
        #verify the message hash
        msg_data = json.dumps(buff)
        #decrypt the message
        try:
            decrypted_data = self.decrypt(message.message["message"])
            
        except Exception as e:
            if self.DEBUG:
                print(f"error decrypting and parsing data : {e}")
            return None
        #get hash and signature
        hash , signature = self.hash_and_sign(msg_data)
        #verify the message hash
        if hash != msg_hash:
            if self.DEBUG:
                print("hash not verified")
            return None
        #verify the message signature
        if signature!=msg_signature:
            if self.DEBUG:
                print("signature not verified")
            return None
        #parse the message
        decrypted_data = json.loads(decrypted_data)
        #check if the message counter is valid
        if decrypted_data["counter"] <= session["counter"]:
            if self.DEBUG:
                print("counter not valid")
            return None
        
        #validate the message
        message.message["message"] = decrypted_data
        try :
            message=ApprovalMessage(message.message)
        except Exception as e:
            if self.DEBUG:
                print(f"error validating message : {e}")
            return None
        
        #first generate symmetric key
        key = decrypted_data["data"]["session_key"]
        #get the session id
        session_id = decrypted_data["data"]["session_id"]
        #decrypt the test message
        try:
            decrypted_test = self.decrypt_symmetric(decrypted_data["data"]["test_message"],key)
            if decrypted_test != "client_test":
                if self.DEBUG:
                    print("test message not decrypted")
                return None
        except Exception as e:
            if self.DEBUG:
                print(f"error decrypting test message : {e}")
            return None
        #create new session
        session_data = {
            "pk": pk,
            "node_id": message.message["node_id"],
            "node_type": message.message["node_type"],
            "last_active": mktime(datetime.datetime.now().timetuple()),
            "port": message.message["port"],
            "role": "server",   
            "counter": message.message["message"]["counter"],
            "session_id": session_id,
            "key": key,
            "status": "active",
            "last_heartbeat": mktime(datetime.datetime.now().timetuple()),
            "approved": True
        }
        self.create_connection_session(session_id,session_data)
        #prepare approval message
        msg_data = OrderedDict({
                "timestamp": str(datetime.datetime.now()),
                "counter": self.comm.counter,
                "data":{
                    "session_id": session_id,
                    "test_message": self.encrypt_symmetric("server_test",key)
                    }
                })
        #stringify the message
        msg_data = json.dumps(msg_data)
        #encrypt the message    
        data_encrypted = self.encrypt(msg_data,self.reformat_public_key(pk))
        payload = OrderedDict({
            "node_id": self.node_id,
            "node_type": self.node_type,
            "pos": self.pos,
            "type": "discovery_approval",
            "port": self.port,
            "session_id": "",
            "message": data_encrypted
            })
        #stringify the payload
        payload_data = json.dumps(payload)
        #get message hash and signature
        data_hash,data_signature = self.hash_and_sign(payload_data)
        #add hash and signature to the message
        payload["hash"] = data_hash
        payload["signature"] = data_signature
        #send the message
        self.put_queue({"target": message.message["node_id"],
                    "message": payload,
                    "pos": self.pos},"outgoing")

    def finalize_discovery(self,message):
        #approve discovery response and add node to the network
        #check if the node does not have active discovery session with the sender
        session = self.get_discovery_session(message.message["node_id"])
        if not session:
            if self.DEBUG:
                print("node does not have active discovery session with the sender")
            return None
        #verify the message hash 
        buff = message.message
        msg_hash = buff.pop('hash')
        msg_signature = buff.pop('signature')
        #verify the message hash
        msg_data = json.dumps(buff)
        #get the public key of the sender from the session
        pk = session["pk"]
        #decrypt the message
        try:
            decrypted_data = self.decrypt(message.message["message"],self.sk)
            
        except Exception as e:
            if self.DEBUG:
                print(f"error decrypting and parsing data : {e}")
            return None
        #get hash and signature
        hash , signature = self.hash_and_sign(msg_data)
        #verify the message hash
        if hash != msg_hash:
            if self.DEBUG:
                print("hash not verified")
            return None
        #verify the message signature
        if signature!=msg_signature:
            if self.DEBUG:
                print("signature not verified")
            return None
        #parse the message
        decrypted_data = json.loads(decrypted_data)
        #check if the message counter is valid
        if decrypted_data["counter"] <= session["counter"]:
            if self.DEBUG:
                print("counter not valid")
            return None
        
        #validate the message
        message.message["message"] = decrypted_data
        try :
            message=ApprovalResponseMessage(message.message)
        except Exception as e:
            if self.DEBUG:
                print(f"error validating message : {e}")
            return None
        
        
        #decrypt the test message
        try:
            decrypted_test = self.decrypt_symmetric(decrypted_data["data"]["test_message"],session["key"])
            if decrypted_test != "server_test":
                if self.DEBUG:
                    print("test message not decrypted")
                return None
        except Exception as e:
            if self.DEBUG:
                print(f"error decrypting test message : {e}")
            return None
        
        #get the session id
        session_id = decrypted_data["data"]["session_id"]
        #update the session
        session_data = {
            "approved": True,
            "status": "active",
        }
        self.update_connection_session(session_id,session_data)
        
 
    ################################
    # session management
    ################################      
    '''
    discovery session shape :
    {
        {
          "node_id": node_id,
            "node_type": node_type,
            "pk": public_key,
            "counter": counter
            "timestamp": timestamp
            "status": status
            "role": role
            "challenge": challenge
            "client_challenge_response": client_challenge_response
            "server_challenge_response": server_challenge_response
            "session_id": session_id  
        }
        
    }
    connection session shape :
    {
        {
          "node_id": node_id,
            "node_type": node_type,
            "pk": public_key,
            "counter": counter
            "timestamp": timestamp
            "status": status
            "role": role
            "challenge": challenge
            "client_challenge_response": client_challenge_response
            "server_challenge_response": server_challenge_response
            "session_id": session_id  
        }
        
    }
    ''' 
    def create_discovery_session(self, node_id, data):
        
        #create new session with the given public key and type
        data["node_id"] = node_id
        #add last call timestamp
        data["last_active"] = mktime(datetime.datetime.now().timetuple())
        self.discovery_sessions[node_id]= data
            
    def update_discovery_session(self, node_id, data):
        #update session with the given public key and type
        for key,value in data.items():
            self.discovery_sessions[node_id][key] = value
        #update last call timestamp
        self.discovery_sessions[node_id]["last_active"] = mktime(datetime.datetime.now().timetuple())
        
    def get_discovery_session(self, node_id):
        #get all discovery sessions
        session = self.discovery_sessions.get(node_id,None)
        if session:
            #update last call timestamp
            self.discovery_sessions[node_id]["last_active"] = mktime(datetime.datetime.now().timetuple()) 
        return session
    
    def has_active_connection_session(self, node_id):
        #check if session with the given public key is active
        for key,value in self.connection_sessions.items():
            if value["node_id"] == node_id:
                return True
        return False
    
    def get_connection_sessions(self,session_id):
        #get connection sessions
        session= self.connection_sessions.get(session_id,None)
        if session:
            #update last call timestamp
            self.connection_sessions[session_id]["last_active"] = mktime(datetime.datetime.now().timetuple())
        return session
           
    def generate_session_id(self):
        #generate session id, random string of 32 characters
        return ''.join(choices(ascii_uppercase + digits, k=32))
        
    def create_connection_session(self, session_id, data):
        #create new session with the given public key and type
        self.connection_sessions[session_id]= data
        
    def update_connection_session(self, session_id, data):
        #update session with the given public key and type
        for key,value in data.items():
            self.connection_sessions[session_id][key] = value
        #update last call timestamp
        self.connection_sessions[session_id]["last_active"] = mktime(datetime.datetime.now().timetuple())
    
    def get_connection_session_by_node_id(self, node_id):
        #get connection session by node id
        for key,value in self.connection_sessions.items():
            if value["node_id"] == node_id:
                return value
        return None
        
    ################################
    # queue management
    ################################
    def put_queue(self, message,msg_type,on_failure=None):
        
        #add message to queue
        self.queue.put({
            "message": message,
            "type": msg_type,
            "on_failure": on_failure
        })
                 
    def pop_queue(self):
        #get message from send queue
        if self.queue.empty():
            return None
        else:
            data = self.queue.get()
            self.queue.task_done()
            return data
    
    ################################
    # Heartbeat management
    ################################
    
    def send_heartbeat(self,session):
        
        #send heartbeat to session
        #prepare message 
        msg_data = OrderedDict({
                "timestamp": str(datetime.datetime.now()),
                "counter": session["counter"]+1,
                "data":None
            })
        #serialize message
        msg_data= json.dumps(msg_data)
        #encrypt message
        encrypted_msg = self.encrypt_symmetric(msg_data,session["key"])
        #create heartbeat message
        payload = OrderedDict({
            "session_id": session["session_id"],
            "node_id": self.node_id,
            "node_type": self.node_type,
            "port": self.port,
            "type": "heartbeat",
            "pos": self.pos,
            "message":encrypted_msg
            })
        #serialize message
        msg_data= json.dumps(payload)
        #get message hash and signature
        msg_hash,msg_signature = self.hash_and_sign(msg_data)
        #add hash and signature to message
        payload["hash"] = msg_hash
        payload["signature"] = msg_signature
        #send message
        self.put_queue({"target": session["node_id"],
                        "message": payload,
                        "pos": self.pos},"outgoing")
           
    def handle_heartbeat(self,message):
        #receive heartbeat from node
        #get session
        session = self.get_connection_sessions(message.message["session_id"])
        if not session:
            if self.DEBUG:
                print("Invalid session")
            return
        
        #get message hash and signature
        buff = message.message.copy()
        msg_hash = buff.pop("hash")
        msg_signature = buff.pop("signature")
        #serialize message buffer
        msg_data= json.dumps(buff)
        #verify message hash and signature
        hash ,signature = self.hash_and_sign(msg_data)
        #verify message hash
        if hash != msg_hash:
            if self.DEBUG:
                print("Invalid hash")
            return
        #verify message signature
        if signature != msg_signature:
            if self.DEBUG:
                print("Invalid signature")
            return
        #decrypt message
        try:
            decrypted_msg = self.decrypt_symmetric(message.message["message"],session["key"])
        except:
            if self.DEBUG:
                print("Invalid key")
            return
        #validate message
        message.message["message"] = json.loads(decrypted_msg)
        #check counter
        if message.message["message"]["counter"]<=session["counter"]:
            if self.DEBUG:
                print("Invalid counter")
            return
        #prepare message 
        msg_data = OrderedDict({
                "timestamp": str(datetime.datetime.now()),
                "counter": session["counter"]+1,
                "data":None
            })
        #serialize message
        msg_data= json.dumps(msg_data)
        #encrypt message
        encrypted_msg = self.encrypt_symmetric(msg_data,session["key"])
        #create heartbeat message
        payload = OrderedDict({
            "session_id": session["session_id"],
            "node_id": self.node_id,
            "node_type":self.node_type,
            "port": self.port,
            "type": "heartbeat_response",
            "pos": self.pos,
            "message":encrypted_msg
            })
        #serialize message
        msg_data= json.dumps(payload)
        #get message hash and signature
        msg_hash,msg_signature = self.hash_and_sign(msg_data)
        #add hash and signature to message
        payload["hash"] = msg_hash
        payload["signature"] = msg_signature
        #send message
        self.put_queue({"target": session["node_id"],
                        "message": payload,
                        "pos": self.pos},"outgoing")
 
    def handle_heartbeat_response(self,message):
        #receive heartbeat from node
        #get session
        session = self.get_connection_sessions(message.message["session_id"])
        if not session:
            if self.DEBUG:
                print("Invalid session")
            return
        
        #get message hash and signature
        buff = message.message.copy()
        msg_hash = buff.pop("hash")
        msg_signature = buff.pop("signature")
        #serialize message buffer
        msg_data= json.dumps(buff)
        #get message hash and signature
        hash,signature = self.hash_and_sign(msg_data)
        #verify message hash and signature
        if hash != msg_hash:
            if self.DEBUG:
                print("Invalid hash")
            return
        #verify message hash
        if signature != msg_signature:
            if self.DEBUG:
                print("Invalid signature")
            return
        #decrypt message
        try:
            decrypted_msg = self.decrypt_symmetric(message.message["message"],session["key"])
        except:
            if self.DEBUG:
                print("Invalid key")
            return
        #validate message
        message.message["message"] = json.loads(decrypted_msg)
        #check counter
        if message.message["message"]["counter"]<session["counter"]:
            if self.DEBUG:
                print("Invalid counter")
            return
        #update session
        self.update_connection_session(message.message["session_id"],{
            "counter":message.message["message"]["counter"],
            "last_active": mktime(datetime.datetime.now().timetuple())})       
        
    def handle_data(self,message):
        #get session
        session = self.get_connection_sessions(message.message["session_id"])
        if not session:
            if self.DEBUG:
                print("Invalid session")
            return
        
        #decrypt message
        try:
            decrypted_msg = self.decrypt_symmetric(message.message["message"],session["key"])
        except:
            if self.DEBUG:
                print("Invalid key")
            return
        #validate message
        message.message["message"] = json.loads(decrypted_msg)
        #check counter
        if message.message["message"]["counter"]<session["counter"]:
            if self.DEBUG:
                print("Invalid counter")
            return
        #print message content 
        self.server.logger.warning(f'{message.message["node_id"]} : {message.message["message"]["data"]["message"]}')

if __name__ == "__main__":
    #node = NetworkInterface("https://webhook.site/da3aee86-1fff-44c0-8f5f-5eeee42e5bc3",500,None)
    secret = "secret"
    auth = '1234567890'
    port = randint(5000,6000)
    node = NetworkInterface("http://127.0.0.1:5000",port,None,secret,auth,True)
    node.start()
