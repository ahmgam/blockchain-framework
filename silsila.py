from .network import CommunicationModule,NetworkInterface

class Silsila:
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
        #define output queue
        self.output_queue = queue.Queue()
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
          