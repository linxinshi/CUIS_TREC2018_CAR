import pymongo
from config import *

class Mongo_Object(object):
      client = None
      db = None
      conn_wiki_aws=None
      conn_acs=None
      conn_wasp=None
      
      def __init__(self,hostname,port):
          self.client = pymongo.MongoClient(hostname,port)
          self.db = (self.client).trec2018
          self.conn_wiki_aws=self.db['wiki_article_with_section_clean_stemmed_v2']
          self.conn_acs=self.db['article_categories']
          self.conn_wasp=self.db['wiki_article_section_paragraph_v2']
          self.conn_qe=self.db[QUERY_ENTITY_COLLECTION]
          
      def __del__(self):
          (self.client).close()