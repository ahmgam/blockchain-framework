from time import mktime
import datetime
from random import choices
from string import digits, ascii_uppercase

class SessionManager:
    def __init__(self):
        #define session manager
        self.discovery_sessions = {}
        self.connection_sessions = {}
   
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
        
    def get_active_nodes(self):
        return [session["node_id"] for session in self.connection_sessions.values() if session["last_active"] > mktime(datetime.datetime.now().timetuple())-60]