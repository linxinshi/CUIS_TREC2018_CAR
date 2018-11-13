# built according to Fielded Sequential Dependence Model
# change number like 10,000 to 10000
# 2018.01.26  add field 'wikipedia' to store text contents of the Wikipedia articles
# by default only consider stemmed fields

import os,sys, string, platform

import lucene
from java.io import File
from java.nio.file import Paths
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.analysis.core import SimpleAnalyzer
from org.apache.lucene.document import Document, Field, StringField, TextField, StoredField
from org.apache.lucene.index import IndexWriter, IndexWriterConfig, DirectoryReader, Term
from org.apache.lucene.store import MMapDirectory
from org.apache.lucene.util import Version
from org.apache.lucene.queryparser.classic import ParseException, QueryParser
from org.apache.lucene.search import IndexSearcher, Query, ScoreDoc, TopScoreDocCollector
from org.apache.lucene.search.similarities import BM25Similarity

from lucene_field import *
from org.apache.lucene.document import FieldType
from lib_process import *
from urllib.request import unquote
from trec_car.read_data import *

# has java VM for Lucene been initialized
lucene_vm_init = False

# global data structure
queries = []

# global parameter
       
def findTitle(line):
    pos=line.find('resource/')
    assert pos!=-1
    return line[pos+9:-1]
     
    
def makeIndex(w):
   # initialize mongodb
    cnt_debug=0
    with open('dedup.articles-paragraphs.cbor', 'rb') as f:
         for p in iter_paragraphs(f):
             cnt_debug+=1
             #if cnt_debug>10:
                #break
             
             if cnt_debug%10000==0:
                print (cnt_debug)
             #entities = [elem.page for elem in p.bodies if isinstance(elem, ParaLink)]
             #print(entities)

             # Print text interspersed with links as pairs (text, link)
             mixed = [(elem.anchor_text, elem.page) for elem in p.bodies if isinstance(elem, ParaLink) ]
             #print(mixed) 
             
             entity_list=[]
             text_list=[]
             for pair in mixed:
                 text,entity=pair
                 title=entity.replace(' ','_')
                 entity_list.append(title)
                 text_list.append(text)
             
             texts=superCleanSentence(' '.join(text_list))
             entities=(' '.join(entity_list)).lower()
             entities_label=superCleanSentence(entities)
             
             '''
             print (p.para_id)
             print (texts)
             print (entities)
             print (entities_label)
             print ('-----------------')
             '''
             
             # store field into dictionary
             data={}
             
             data['id']=(p.para_id,'StringField') 
             data['anchor_text']=(texts,'CUSTOM_FIELD_TEXT_BF')
             data['entities']=(entities,'CUSTOM_FIELD_TEXT_BF')
             data['entities_label']=(entities_label,'CUSTOM_FIELD_TEXT_BF')
            
             addDoc(w,data)
    
    
def addDoc(w,data):
    doc = Document()
    #print ('----------------------------')
    for field in data:
        value,type=data[field][0],data[field][1]
        '''
        print ('field:%s  type:%s'%(field,type))
        print (value+'\n')
        '''
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

def main():
    try:
       lucene.initVM(vmargs=['-Djava.awt.headless=true'])
       lucene_vm_init = True
    except:
       print ('JavaVM already running')
       
    LUCENE_INDEX_DIR='mmapDirectory\\trec_v21_para_uri'   
    is_index_Exist = os.path.exists(LUCENE_INDEX_DIR)
    # specify index path 
    index_mm = MMapDirectory(Paths.get(LUCENE_INDEX_DIR))
    
    # configure search engine
    analyzer = SimpleAnalyzer()
    config = IndexWriterConfig(analyzer)
    config=config.setRAMBufferSizeMB(512.0)  # experimental setting !!
    # write data to index
    
    #if not is_index_Exist:
    if True:
       print ('begin backup code files')
       system_flag=platform.system()
       if system_flag=='Windows':
          cmd='robocopy %s %s\code_files *.py'%(r'%cd%',LUCENE_INDEX_DIR)
          os.system(cmd)
       else:
          cmd='mkdir %s/code_files'%(LUCENE_INDEX_DIR)
          os.system(cmd)
          cmd='cp -f *.py %s/code_files'%(LUCENE_INDEX_DIR)
          os.system(cmd)
        
       w = IndexWriter(index_mm,config)
       makeIndex(w)
       w.close()
    else:
       print ('index already exists, stop indexing')

if __name__ == '__main__':
   main()