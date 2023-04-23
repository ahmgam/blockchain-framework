'''
This is Point-to-Point Protocol (P2P) message format for the network peer discovery and data transfer.

Network peer discovery message format:
{
    
    "type": "discovery",
    "node_id": "node id"
    "node_type": "node type"
    "port": "port"
    "pos": "position"
    "session_id": "[discovery/data]-session id"
    "message":{
        "timestamp": "timestamp"
        "counter": "counter"
        data: {
            "pk": "public key"
        }
    }
    "hash": "hash"
    "signature": "signature"
}

Network peer discovery response message format:
{
    "node_id": "node id",
    "node_type": "node type"
    "pos": "position"
    "port": "port"
    "type": "discovery_response",
    "session_id": "[discovery/data]-session id"
*   "message":{
        "timestamp": "timestamp"
        "counter": "counter"
        "data":{
            "pk": "public key"
        }
    }
    "hash": "hash"
    "signature": "signature"
}

Network peer discovery verification message format:
{
    "node_id": "node id",
    "node_type": "node type"
    "pos": "position"
    "port": "port"
    "type": "discovery_verification",
    "session_id": "[discovery/data]-session id"
*   "message": {
        "timestamp": "timestamp"
        "counter": "counter"
        "data":{
            "challenge": "challenge"
            "client_challenge_response": "challenge_response"
        }
        
    }
    "hash": "hash"
    "signature": "signature"
}


Network Peer discovery verification response message format:
{
    "node_id": "node id",
    "node_type": "node type"
    "pos": "position"
    "port": "port"
    "type": "discovery_verification_response",
    "session_id": "[discovery/data]-session id"
    "message: {
        "timestamp": "timestamp"
        "counter": "counter"
        "data":{
            "challenge": "challenge"
            "server_challenge_response": "challenge_response"
            }
    }
    "hash": "hash"
    "signature": "signature"
    
}
Network peer approval message format:
{
    "node_id": "node id",
    "node_type": "node type"
    "pos": "position"
    "port": "port"
    "type": "discovery_approval",
    "session_id": "[discovery/data]-session id"
    "message: {
        "timestamp": "timestamp"
        "counter": "counter"
        "data":{
            "session_id": "session id"
            "session_key": "session key"
            "test_message": "test message"
            }
    }
    "hash": "hash"
    "signature": "signature"
    
}
Network peer approval response message format:
{
    "node_id": "node id",
    "node_type": "node type"
    "pos": "position"
    "port": "port"
    "type": "approval_response",
    "session_id": "[discovery/data]-session id"
    "message: {
        "timestamp": "timestamp"
        "counter": "counter"
        "data":{
            "session_id": "session key"
            "test_response": "test response"
            }
    }
    "hash": "hash"
    "signature": "signature"
}

Network peer heartbeat message format:
{
    "node_id": "node id",
    "node_type": "node type"
    "pos": "position"
    "port": "port"
    "session_id": "[discovery/data]-session id"
    "type": "heartbeat",
    "message":{
        "timestamp": "timestamp"
    }
    
    
}

Network peer heartbeat response message format:
{
    "session_id": "[discovery/data]-session id"
    "node_id": "node id",
    "node_type": "node type"
    "pos": "position"
    "port": "port"
    "type": "heartbeat_response",
    "message":{
        "timestamp": "timestamp"
        "counter": "counter"
    }
}

Network peer data message format:
{
 
    "session_id": "[discovery/data]-session id"
    "node_id": "node id",
    "node_type": "node type"
    "pos": "position"
    "port": "port"
    "type": "data_message",
    "message":{
        "timestamp": "timestamp"
        "counter": "counter"
        "data": {}
    }
}


'''

import json
from hashlib import sha256
from collections import OrderedDict

class Message :
    def __init__(self,data, **kwargs):
        #validate the message
        self.__validate(data)
        #save the message
        self.message =OrderedDict( data)
        #check if required fields are present
        if "required_fields" in kwargs:
            self.__check_required_fields(kwargs["required_fields"],data)
        
            
    def __check_required_fields(self,required_fields,data):
        if not isinstance(required_fields,list):
            print("required_fields must be a list")
            raise TypeError("required_fields must be a list")    
        for value in required_fields:
            if value not in data["message"]["data"].keys():
                print("field {} is required".format(value))
                raise ValueError("field {} is required".format(value))

    def __validate(self,data):
        #validate the message
        #if not (isinstance(data,dict) or isinstance(data,OrderedDict)):
        #    raise TypeError("data must be a dictionary")
        for key in ["type","session_id","node_id","message","node_type","pos","port"]:
            if key not in data:
                raise ValueError("field {} is required".format(key))

            
    def __repr__(self):
        return json.dumps(self.message)
    
    def __str__(self):
        return json.dumps(self.message)

    def to_dict(self):
        return dict(self.message)
    
    def to_json(self):
        return json.dumps(self.message)
        
    def sign(self, private_key):
        #sign the message
        self.message["signature"] = private_key.sign(self.message["hash"].encode("utf-8"))
        

    
class DiscoveryMessage(Message):
    def __init__(self,data):
        #definte required fields
        required_fields = ["pk"]
        super().__init__(data,required_fields=required_fields)
        
class DiscoveryResponseMessage(Message):
    def __init__(self,data):
        #definte required fields
        required_fields = ["pk"]
        super().__init__(data,required_fields=required_fields)  
              
class VerificationMessage(Message):
    def __init__(self,data):
        #definte required fields
        required_fields = ["challenge","client_challenge_response"]
        super().__init__(data,required_fields=required_fields)
   
class VerificationResponseMessage(Message):
    def __init__(self,data):
        #definte required fields
        required_fields = ["challenge","server_challenge_response"]
        super().__init__(data,required_fields=required_fields)   
        
class ApprovalMessage(Message):
    def __init__(self,data):
        #definte required fields
        required_fields = ["session_id","session_key","test_message"]
        super().__init__(data,required_fields=required_fields) 
        
class ApprovalResponseMessage(Message):
    def __init__(self,data):
        #definte required fields
        required_fields = ["session_id","test_message"]
        super().__init__(data,required_fields=required_fields)
                
if __name__ == "__main__":
    m = Message("public_key",type="discovery")
    print(m)
    print(m.get_hash())
    print(m.get_timestamp())
    print(m.generate_id())
    print(m)