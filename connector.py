from .authentication import Authentication,Peer
import uuid
class Connector:
    
    def __init__(self):
        '''
        initialize the connector
        '''
        self.peer_list = []
        #initialize the authenticator
        self.authenticator = Authentication(self.peer_list)
        #generate session key
        self.session_key = self.generateSessionKey()
        #generate public key
        self.public_key = self.authenticator.generate_public_key()
        
    def addPeer(self, peerInfo):
        '''
        add a peer to the peer list
        @param peerInfo: the peer information
        '''
        try:
            self.peer_list.append(Peer(peerInfo))
        except:
            raise Exception('peer information is not valid')
        
    def generateSessionKey(self):
        '''
        generate the session key
        '''
        #generate session key as random string
        return str(uuid.uuid4())
    
    def generatePublicKey(self):
        '''
        generate the public key
        '''
        
        return 