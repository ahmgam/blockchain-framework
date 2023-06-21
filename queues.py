
import queue
from time import mktime
import datetime

class QueueManager:
    
    def __init__(self):
        self.queue = queue.Queue()
        self.output_queue = queue.Queue()
        
    def put_queue(self, message,msg_type,on_failure=None):
        
        #add message to queue
        self.queue.put({
            "message": message,
            "type": msg_type,
            "on_failure": on_failure
        })
                 
    def pop_queue(self):
        #get message from send queue
        if self.queue.empty():
            return None
        else:
            data = self.queue.get()
            self.queue.task_done()
            return data
    
    def put_output_queue(self, message,msg_source,msg_type):
        
        #add message to queue
        self.output_queue.put({
            "message": message,
            "source": msg_source,
            "type": msg_type,
            "timestamp": mktime(datetime.datetime.now().timetuple())
        })
    def pop_output_queue(self):
        #get message from send queue
        if self.output_queue.empty():
            return None
        else:
            data = self.output_queue.get()
            self.output_queue.task_done()
            return data    