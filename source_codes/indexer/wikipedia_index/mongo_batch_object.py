import pymongo

class Mongo_Batch_Object(object):
      cnt_batch=None
      batch=None
      cnt_limit=None
      
      def __init__(self,cnt_limit=2000):
          self.cnt_batch=0
          self.cnt_limit=cnt_limit
          self.batch=[]
      
      def insert(self,doc,conn):
          self.cnt_batch+=1
          self.batch.append(doc)
          
          if self.cnt_batch>self.cnt_limit:
             conn.insert_many(self.batch)
             self.cnt_batch=0
             del self.batch[:]
             
      def cleanInsert(self,conn):
          if self.cnt_batch>0:
             conn.insert_many(self.batch)
             self.cnt_batch=0
             del self.batch[:]        
     