

class Authentication:
    def __init__(self, peer_list):
        '''
        initialize the authentication class, which is used to authenticate the node
        @param peer_list: the peer list
        '''
        #initialize peers
        try:
            self.peers = [Peer(peer) for peer in peer_list]
        except:
            raise Exception('peer list is not valid')

    def whoAmI(self):
        '''
        return the node information of the node
        '''
        #get mac address
        
        return self.peer_list[0].get_node_inf()
        
    
    
    def encrypt(self, message):
        try:
            #get public key from peer list
            public_key = self.peer_list[0].get_public_key()
            #encrypt message
            encrypted_message = public_key.encrypt(message, 32)
            return encrypted_message
        except:
            return None
            
            
class Peer:
    def __init__(self, peerInfo):
        '''
        initialize the peer class
        @param peerInfo: the peer information
        '''
        try:
            self.peerSecret = peerInfo["secret"]
            self.peerId = peerInfo["id"]
            self.public_key = None
        except Exception as e:
            raise Exception('peer information is not valid')
    def encrypt(self, message):
        '''
        encrypt the message
        @param message: the message to be encrypted
        '''
        return self.public_key.encrypt(message, 32)
    
    def getPublicKey(self):
        '''
        get the public key of the peer
        '''
        return self.public_key
    
    def setPublic_key(self, public_key):
        '''
        set the public key of the peer
        @param public_key: the public key of the peer
        '''
        self.public_key = public_key
        
        
        
        