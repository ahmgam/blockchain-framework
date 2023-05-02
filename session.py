from time import mktime
import datetime
from random import choices
from string import digits, ascii_uppercase
from collections import OrderedDict
from encryption import EncryptionModule
class SessionManager:
    def __init__(self,parent):
        #define session manager
        self.parent = parent
        self.discovery_sessions =OrderedDict()
        self.connection_sessions = OrderedDict()
        self.node_states = OrderedDict({self.parent.node_id:{"pk":EncryptionModule.format_public_key(self.parent.pk),"last_active":mktime(datetime.datetime.now().timetuple())}})
   
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
        #refresh node state table
        self.refresh_node_state_table()
        
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
        
    def get_active_nodes(self):
        return [session["node_id"] for session in self.connection_sessions.values() if session["last_active"] > mktime(datetime.datetime.now().timetuple())-60]

    def get_active_nodes_with_pk(self):
        return [{session["node_id"]:session["pk"]} for session in self.connection_sessions.values() if session["last_active"] > mktime(datetime.datetime.now().timetuple())-60]
    
    def get_node_state_table(self):
        #refresh node state table
        self.refresh_node_state_table()
        #get nodes in state table
        response = {}
        for key,value in self.node_states.items():
            if value["last_active"] > mktime(datetime.datetime.now().timetuple())-60:
                response[key] = value["pk"]
        return response
    
    
    def update_node_state_table(self,table):
        #refresh node state table
        self.refresh_node_state_table()
        #update node state table
        for key,value in table.items():
            #check if node is already in node state table
            if key in self.node_states.keys():
                #update last call timestamp
                self.node_states[key]["last_active"] = mktime(datetime.datetime.now().timetuple())
                continue
            #update last call timestamp
            self.node_states[key] = {"pk":value,"last_active":mktime(datetime.datetime.now().timetuple())}
            
    def compare_node_state_table(self,table):
        #refresh node state table
        self.refresh_node_state_table()
        #compare node state table
        for key,value in table.items():
            #check if node is already in node state table
            if key in self.node_states.keys():
                if self.node_states[key]["pk"] == value:
                    continue
                else:
                    return False
        return True
    
    def refresh_node_state_table(self):
        #refresh node state table
        for key,value in self.connection_sessions.items():
            if value["node_id"] in self.node_states.keys():
                continue
            else:
                self.node_states[value["node_id"]] = {"pk":value["pk"],"last_active":mktime(datetime.datetime.now().timetuple())}
