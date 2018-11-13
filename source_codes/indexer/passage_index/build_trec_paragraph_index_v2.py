# v2 source: paragraphcorpus.cbor
from urllib.request import unquote
from trec_car.read_data import *
from lib_process import *
import pymongo
import platform, os

import lucene
from java.io import File
from java.nio.file import Paths
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.document import Document, Field, StringField, TextField, StoredField
from org.apache.lucene.index import IndexWriter, IndexWriterConfig, DirectoryReader, Term
from org.apache.lucene.store import MMapDirectory
from org.apache.lucene.util import Version
from org.apache.lucene.queryparser.classic import ParseException, QueryParser
from org.apache.lucene.search import IndexSearcher, Query, ScoreDoc, TopScoreDocCollector
from org.apache.lucene.search.similarities import BM25Similarity
from org.apache.lucene.search import PhraseQuery, BooleanQuery, TermQuery, BooleanClause

from lucene_field import *
from org.apache.lucene.document import FieldType

def addDoc(w,data):
    doc = Document()
    #print ('----------------------------')
    for field in data:
        value,type=data[field][0],data[field][1]
        #print ('field:%s  type:%s'%(field,type))
        #print (value+'\n')
        
        if type=='StringField':
           doc.add(StringField(field,value,Field.Store.YES))
        elif type=='TextField':
           doc.add(TextField(field,value,Field.Store.YES))
        elif type=='CUSTOM_FIELD_TEXT':
           doc.add(Field(field,value,CUSTOM_FIELD_TEXT))
        elif type=='CUSTOM_FIELD_TEXT_DF':
           doc.add(Field(field,value,CUSTOM_FIELD_TEXT_DF))
        elif type=='CUSTOM_FIELD_TEXT_BF':
           doc.add(Field(field,value,CUSTOM_FIELD_TEXT_BF))
        elif type=='INTEGER_STORED':
           doc.add(StoredField(field,value))
        else:
           print ('UNKNOWN FIELD')
           
    w.addDocument(doc)

def cleanText(text):
    text=text.replace('Category:',' ')
    text=superCleanSentence(text)
    return text

def makeIndex(w):
    '''
    if platform.system()=='Windows':
       port=27017
    else:
       port=58903
    client = pymongo.MongoClient('localhost',port)
    db=client.trec2018
    '''
    
    files = ['dedup.articles-paragraphs.cbor']       
    cnt_debug=0

    for item in files:
        with open(item, 'rb') as f:
            #try:
             for p in iter_paragraphs(f):
                 cnt_debug+=1
                 #if cnt_debug>30:
                    #break                 
                 if cnt_debug%10000==0:
                    print ('%d processed'%(cnt_debug))                 
                 
                 #continue
                 
                 text=p.get_text()
                 if text.find('#REDIRECT')>-1:
                    continue
                    
                 text=cleanText(text)
                 data={}
                 data['id']=(p.para_id,'StringField')
                 data['stemmed_catchall']=(text,'CUSTOM_FIELD_TEXT_BF')
                 addDoc(w,data)
            #except:
              #pass
    print (cnt_debug)
    #client.close()
    
def main():
    LUCENE_INDEX_DIR='mmapDirectory/trec_v15_paragraph_stemmed_v2'
    try:
       lucene.initVM(vmargs=['-Djava.awt.headless=true'])
       lucene_vm_init = True
    except:
       print ('JavaVM already running')
       
    is_index_Exist = os.path.exists(LUCENE_INDEX_DIR)
    # specify index path 
    index_mm = MMapDirectory(Paths.get(LUCENE_INDEX_DIR))
    
    # configure search engine
    analyzer = StandardAnalyzer()
    config = IndexWriterConfig(analyzer)
    #config=config.setRAMBufferSizeMB(1024.0)
    # write data to index
    
    if not is_index_Exist:
    #if True:
       print ('begin backup code files')
       system_flag=platform.system()
       if system_flag=='Windows':
          os.system('robocopy %s %s\code_files *.py'%(r'%cd%',LUCENE_INDEX_DIR))
       else:
          os.system('mkdir %s/code_files'%(LUCENE_INDEX_DIR))
          os.system('cp *.py %s/code_files'%(LUCENE_INDEX_DIR))
        
       w = IndexWriter(index_mm,config)
       makeIndex(w)
       w.close()
    else:
       print ('index already exists, stop indexing')       

if __name__ == '__main__':
   main()