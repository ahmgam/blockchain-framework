import datetime
import requests
class CommunicationModule:
    def __init__(self,parent):
        self.parent = parent
        self.counter = 0
        self.timeout = 5
    def send(self, message):
        if self.parent.DEBUG:
            print(f'{datetime.datetime.now()} : Sending message to {message["target"]} with type {message["message"]["type"]}')
        headers = {'Content-Type': 'application/json'}
        if self.parent.auth != None:
            headers['Authorization'] = self.parent.auth
        try:
            req =   requests.post(self.parent.endpoint+'/',
                                json = message,
                                headers = headers,timeout=self.timeout)
        except Exception as e:
            if self.parent.DEBUG:
                print(f"Error sending message: {e}")
            return False
        if req.status_code == 200:
            self.counter += 1
            return True
        else :
            if self.parent.DEBUG:
                print(f"Error sending message: {req.status_code}")
            return False