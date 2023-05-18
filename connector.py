import datetime
import requests
from flask import Flask, request
from queue import Queue

class CommunicationModule:
    def __init__(self,node_id,endpoint,port,auth=None,DEBUG=False):
        self.node_id = node_id
        self.server = Flask(__name__)
        self.server.add_url_rule('/', 'listen',lambda : self.listen(self), methods=['POST'])
        self.server.add_url_rule('/send', 'send',lambda : self.send_message(self), methods=['POST'])
        self.endpoint = endpoint
        self.port = port
        self.auth = auth
        self.DEBUG = DEBUG
        self.buffer = Queue()
        self.counter = 0
        self.timeout = 5
    def send(self, message):
        if self.DEBUG:
            print(f'{datetime.datetime.now()} : Sending message to {message["target"]} with type {message["message"]["type"]}')
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
        
    @staticmethod
    def listen(self):
        '''
        receive message from the network
        '''
        #add to buffer
        data = request.json
        self.buffer.put({
            "message":data,
            "type":"incoming"
        })
        return "OK"
    
    def get(self):
        if self.buffer.empty():
            return None
        else:
            return self.buffer.get()
        
    def is_available(self):
        return not self.buffer.empty()

    @staticmethod
    def send_message(self):
        '''
        Send message to the given public key
        '''
        #get data 
        data = request.json
        message = data["message"]
        #payload 
        payload = {
            "message":message,
            "source":self.node_id
        }
        #add message to the parent queue
        self.buffer.put({
            "message":payload,
            "type":"consensus"   
        })
        return True
    
    def start(self):
        self.server.run(port=self.port,debug=self.DEBUG)