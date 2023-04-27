from random import choices
from string import ascii_lowercase
import json
class SBFT:
    def __init__(self,parent) -> None:
        #define parent
        self.parent = parent
        #define views
        self.views = {}
        
    def handle(self, msg):
        #handle message
        operation = msg['operation']
        if operation == 'pre-prepare':
            self.pre_prepare(msg)
        elif operation == 'prepare':
            self.prepare(msg)
        elif operation == 'prepare-collect':
            self.prepare_collect(msg)
        elif operation == 'commit':
            self.commit(msg)
        elif operation == 'commit-collect':
            self.commit_collect(msg)
        else:
            print(f"Received message from {msg['message']['node_id']} of type {msg['message']['type']}, but no handler found")
        pass
    
    def send(self,msg):
        #check message type 
        if type(msg['message']) != dict:
            if self.parent.DEBUG:
                print("Invalid message type")
            return
        #create view number 
        view_id = self.generate_view_id()
        #create view
        self.views[view_id] = {
            "source": self.parent.node_id,
            "message":msg['message'],
            "prepare":{},
            "commit":{},
            "view_id":view_id
            }
        #add view to message
        msg['message']['view_id'] = view_id
        #broadcast message to the network
        self.parent.network.send_message("all",msg)
    
    def pre_prepare(self,msg):
        #handle pre-prepare message
        pass
    
    def prepare(self,msg):
        #handle prepare message
        pass
    
    def prepare_collect(self,msg):
        #handle prepare-collect message
        pass
    
    def commit(self,msg):
        #handle commit message
        pass
    
    def commit_collect(self,msg):
        #handle commit-collect message
        pass
    
    def generate_view_id(self,length=8):
        #generate view id
        return ''.join(choices(ascii_lowercase, k=length))