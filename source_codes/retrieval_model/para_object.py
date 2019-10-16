import sys,datetime 
from nltk.stem.snowball import SnowballStemmer
from lib_process import *
from list_term_object import List_Term_Object
from config import *
from doc_tree_object import Doc_Tree_Object

from document_object import Document_Object
from nltk.util import ngrams

class Para_Object(Document_Object):
      #__slots__=('id','title','name','raw_name','value','category','abstract','all_text_obj','attribute_obj','category_obj','name_obj','abstract_obj','en_ens','en_vector','mentioned_entity','rel_vec')    
      categories=None
      dict_obj=None
      bigrams=None
      article_title=None
      section_title=None
      
      mentioned_entity=None
      
      wiki_doc_tree=None
      term_freq=None
      term_freqs=None
      lengths=None
      
      def __init__(self):
          self.dict_obj={}
          self.dict_attr={}
      
      def update_article_title(self,mongoObj):
          temp=findOneDBEntry(mongoObj.conn_wasp,'paragraphID',self.id,'title')      
          if temp is not None:
             self.article_title=temp
          else:
             self.article_title='NONE'
             #print ('error id=%s'%(self.para_id))
          
      def updateFromIndex(self,d_pair,mongoObj,lucene_obj):
          # d_pair:(document,docid) para: dict   
          para,docid=d_pair[0],d_pair[1]
          for idf in para.iterator():
              self.setAttr(idf.name(),idf.stringValue())
              #print ('%s\t%s'%(idf.name(),idf.stringValue()))   
              
          self.setAttr('para_id',self.id)
          
          self.update_article_title(mongoObj)
          
          if IS_SAS_USED==True:
             self.update_categories(mongoObj)
          self.update_term_freq(docid,USED_CONTENT_FIELD,lucene_obj)
          self.length=sum(self.term_freq.values())  
          
          if IS_WIKI_DOC_TREE_USED==True:
             article=findOneDBEntry(mongoObj.conn_wiki_aws,'title',self.article_title,'article')
             if article is not None:
                self.wiki_doc_tree=Doc_Tree_Object(article)
                #self.wiki_doc_tree.title=self.wiki_id
          
      def update_term_freq(self,docid,field,lucene_obj):
          self.term_freq=lucene_obj.get_term_freq(docid,field,False)
          #print (self.term_freq)
                    
      def update_categories(self,mongoObj):
          conn=mongoObj.conn_acs
          field='categories'
          if conn==None:
             return
          item=conn.find_one({'title':self.article_title})
          if item is None:
             self.categories=[]
             return
          self.categories=item[field]                          
