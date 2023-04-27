import rsa
import os
from cryptography.fernet import Fernet
from base64 import  b64encode, b64decode
import json
from math import ceil
import time

class EncryptionModule:
    
    @staticmethod
    def generate_keys():
        '''
        generate new public and private key pair
        '''
        
        #generate new public and private key pair
        pk, sk=rsa.newkeys(2048)
        return pk, sk
    
    @staticmethod
    def store_keys(public_key_file,private_key_file,pk,sk):
        '''
        store public and private key pair in file
        '''
        
        #store public and private key pair in file
        # Save the public key to a file
        with open(public_key_file, 'wb') as f:
            f.write(pk.save_pkcs1())

        # Save the private key to a file
        with open(private_key_file, 'wb') as f:
            f.write(sk.save_pkcs1())
        return None
    
    @staticmethod
    def load_keys(pk_file,sk_file):
        '''
        load public and private key pair from file
        '''
        #check if key pairs is available
        if os.path.isfile(pk_file) and os.path.isfile(sk_file):
            #load public and private key pair from file
            with open(pk_file, 'rb') as f:
                pk = rsa.PublicKey.load_pkcs1(f.read())
            with open(sk_file, 'rb') as f:
                sk = rsa.PrivateKey.load_pkcs1(f.read())
            return pk, sk
        else:        
            return None, None
        
    @staticmethod
    def hash(message):
        '''
        hash message using SHA-256
        '''
        if type(message) == dict:
          message = json.dumps(message)
        return b64encode(rsa.compute_hash(message.encode('utf-8'), 'SHA-256')).decode('ascii')

    @staticmethod
    def sign_hash(message,sk):
      #define private key instance from string
        if type(sk) == str:
            sk = rsa.PrivateKey.load_pkcs1(sk)
        message = b64decode(message.encode('ascii'))
        signature = rsa.sign_hash(message, sk, 'SHA-256')
        return b64encode(signature).decode('ascii')


    @staticmethod
    def sign(message,sk):
        #define private key instance from string
        if type(sk) == str:
            sk = rsa.PrivateKey.load_pkcs1(sk)
        if type(message) == dict:
            message = json.dumps(message)
        signature = rsa.sign(message.encode("utf-8"), sk, 'SHA-256')
        return b64encode(signature).decode('ascii')
        
    @staticmethod
    def verify(message,signature,pk):
        #define public key instance from string
        if type(pk) == str:
            pk = rsa.PublicKey.load_pkcs1(pk)
        #verify signature
        try : 
          if rsa.verify(json.dumps(message).encode("utf-8"), b64decode(signature.encode('ascii')), pk):
            return True
        except:
          return False
        
    @staticmethod
    def format_public_key(pk):
        #remove new line characters
        pk = str(pk.save_pkcs1().decode('ascii'))
        pk = pk.replace('\n-----END RSA PUBLIC KEY-----\n', '').replace('-----BEGIN RSA PUBLIC KEY-----\n','')
        return pk
        
    @staticmethod
    def reformat_public_key(pk):
        return f"-----BEGIN RSA PUBLIC KEY-----\n{str(pk)}\n-----END RSA PUBLIC KEY-----\n"
       
    @staticmethod 
    def generate_symmetric_key():
        return Fernet.generate_key().decode("ascii")
         
    @staticmethod
    def encrypt(message, pk):
        if type(pk) == str:
            pk = rsa.PublicKey.load_pkcs1(pk)
        #encrypt message
        result = []
        for i in range (ceil(len(message)/245)):
            start_index = i*245
            end_index = (i+1)*245 if (i+1)*245 < len(message) else len(message)
            result.append(rsa.encrypt(message[start_index:end_index].encode("ascii"), pk))   
        return b64encode(b''.join(result)).decode('utf-8')
    
    @staticmethod
    def decrypt(message,sk):
        #decrypt message
        message = b64decode(message.encode('utf-8'))
        try:
            result = []
            for i in range (ceil(len(message)/256)):
                start_index = i*256
                end_index = (i+1)*256 if (i+1)*256 < len(message) else len(message)
                result.append(rsa.decrypt(message[start_index:end_index], sk).decode("ascii"))   
            return ''.join(result)
        except Exception as e:
            print(f"error decrypting message: {e}")
            return None
    
    @staticmethod
    def encrypt_symmetric(message,key):
        f = Fernet(key.encode("ascii"))
        return b64encode(f.encrypt(message.encode("utf-8"))).decode('utf-8')
    
    @staticmethod
    def decrypt_symmetric(ciphertext,key):
        f = Fernet(key.encode("ascii"))
        return f.decrypt(b64decode(ciphertext.encode('utf-8'))).decode("ascii")