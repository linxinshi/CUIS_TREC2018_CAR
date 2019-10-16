# -*- coding: utf-8 -*-

from multiprocessing import Process,Manager
import os, sys, argparse, time, datetime
from query_object import Query_Object
from para_object import Para_Object
from mongo_object import Mongo_Object
from structure_object import Structure_Object
from lucene_object import Lucene_Object
from list_term_object import List_Term_Object
from lib_process import *
from lib_metric import *
from config import *
from config_object import *

import lucene
from java.io import File
from java.nio.file import Paths
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.document import Document
from org.apache.lucene.index import IndexWriter, IndexWriterConfig, DirectoryReader, Term
from org.apache.lucene.store import MMapDirectory
from org.apache.lucene.queryparser.classic import QueryParserBase, ParseException, QueryParser, MultiFieldQueryParser
from org.apache.lucene.search import IndexSearcher, Query, ScoreDoc, TopScoreDocCollector, TermQuery, TermRangeQuery
from org.apache.lucene.search.similarities import BM25Similarity

from queue import Queue
import heapq

def read_query(queries,conf_paras):
    src = open(conf_paras.QUERY_FILEPATH,'r',encoding='utf-8')
    cnt_debug=0
    for line in src:
        query = line.strip()
        cnt_debug+=1
        #if cnt_debug>100:
           #break
        queries.append(query) # e.g. Glass%20ceiling/History
    src.close()
    
def computeScore(queryObj,paraObj,structure,lucene_handler,conf_paras):
    mongoObj,paraScore=structure.mongoObj,structure.paraScore
    lucene_obj=lucene_handler['first_pass']
    para_id=paraObj.para_id
    if para_id in paraScore:
       return paraScore[para_id]
  
    # compute text_sim   
    
    text_sim=0.0

    if MODEL_NAME=='lm':      
       text_sim=lmSim(queryObj.contents_obj,paraObj,USED_CONTENT_FIELD,lucene_obj) 
    elif MODEL_NAME=='sdm':
        text_sim=sdmSim(queryObj,paraObj,USED_CONTENT_FIELD,lucene_obj)
        #text_sim=fsdmSim(queryObj,paraObj,lucene_obj)
    elif MODEL_NAME=='fsdm':
        text_sim=fsdmSim(queryObj,paraObj,lucene_obj)
    
    score=text_sim

    return score

def createGraph(queryObj,lucene_handler,structure,conf_paras):
    lucene_obj=lucene_handler['first_pass']
    mongoObj=structure.mongoObj,
    paraScore,paraObjects=structure.paraScore,structure.paraObjects
    
    candidates=[]
    cnt=0
    
    for para_id in structure.currentPara:
        paraScore[para_id] = computeScore(queryObj,paraObjects[para_id],structure,lucene_handler,conf_paras)
        candidates.append((paraScore[para_id],cnt,para_id))
        cnt+=1
    return candidates

def createParaObject(d_pair,structure,lucene_obj):
    #d_pair:(document,docid)
    d=d_pair[0]
    para_id=d.get('id')

    paraObjects=structure.paraObjects
    if para_id not in paraObjects:
       paraObj=Para_Object()
       paraObj.updateFromIndex(d_pair,structure.mongoObj,lucene_obj)
       paraObjects[para_id]=paraObj
    structure.currentPara.add(para_id)
    return paraObjects[para_id]
             
def handle_process(id_process,queries,RES_STORE_PATH,conf_paras):
    starttime=datetime.datetime.now()
    
    structure=Structure_Object(conf_paras,id_process)
    lucene_handler={}
    lucene_handler['first_pass']=Lucene_Object(conf_paras.LUCENE_INDEX_DIR,'BM25',False,True,structure.mongoObj)
    
    RESULT_FILENAME=os.path.join(RES_STORE_PATH,'pylucene_%d.runs'%(id_process))    
    rec_result=open(RESULT_FILENAME,'w',encoding='utf-8')
    # search
    candidates=[]    
    
    for i in range(len(queries)):
        lucene_obj=lucene_handler['first_pass']
        # build query object for computeScore
        queryObj=Query_Object(queries[i],structure,lucene_handler,False)
        querystr=queryObj.querystr   # no stemming may encourter zero candidates if field contents has stemming
        docs=lucene_obj.retrieve(querystr,USED_CONTENT_FIELD,hitsPerPage)
        
        # initialize duplicate remover and score record
        structure.clear()
        del candidates[:]
                
        # find candidate results after 1st round filter
        # d_pair:(document,docid)
        for d_pair in docs:
            d=d_pair[0]
            if d is None:
               continue
            para_id=d['id']
            if para_id in structure.currentPara:
               continue    
            obj=createParaObject(d_pair,structure,lucene_obj)  
        
        candidates=createGraph(queryObj,lucene_handler,structure,conf_paras)
        print ('id_process=%d\t %d/%d\t query=%s  len_docs=%d'%(id_process,i+1,len(queries),queryObj.querystr,len(docs)))
        
            
        # output results from priority queue larger score first
        candidates.sort(key=lambda pair:pair[0],reverse=True)
        
        for rank in range(min(1000,len(candidates))):
            item=candidates[rank]
            para_id=item[2]
            res_line="%s %s %s %d %f %s\n" %(queryObj.queryID,'Q0',para_id,rank+1,item[0],RUN_NAME)
            rec_result.writelines(res_line)
            
    rec_result.close()
    interval=(datetime.datetime.now() - starttime).seconds
    print ('id_process=%d   running time=%s' %(id_process,str(interval)))
           
def main(conf_paras):
    system_flag=conf_paras.system_flag
    
    starttime_total=datetime.datetime.now()
    parser = argparse.ArgumentParser()
    parser.add_argument("-comment", help="comment for configuration", default='')
    args = parser.parse_args()
    
    # generate folder to store results
    if (len(args.comment.strip()))>0:
       comment='-'.join(args.comment.split(' '))
       RES_STORE_PATH=os.path.join(str(datetime.datetime.now()).replace(':','-').replace(' ','-')[:-7]+'-'+comment)
    else:
       RES_STORE_PATH=str(datetime.datetime.now()).replace(':','-').replace(' ','-')[:-7]   
    
    RES_STORE_PATH=os.path.join('CAR_result',RES_STORE_PATH)
       
    print ('store_path=%s'%(RES_STORE_PATH))
    os.mkdir(RES_STORE_PATH)
  
    print ('begin backup code files')
    if system_flag=='Windows':
       cmd='robocopy %s %s *.py'%(r'%cd%',RES_STORE_PATH)
    else:
       cmd='cp *.py %s'%(RES_STORE_PATH)
    os.system(cmd)
    # read queries
    queries=[]
    read_query(queries,conf_paras)
    cnt_query=len(queries)
   
   # begin multiprocessing
    process_list=[]
    num_workers=NUM_PROCESS
    delta=cnt_query//num_workers  
    if cnt_query%num_workers!=0:  # +1 important
       delta=delta+1
    
    for i in range(num_workers):
        left=i*delta
        right=(i+1)*delta
        if right>cnt_query:
           right=cnt_query
         
        p = Process(target=handle_process, args=(i,queries[left:right],RES_STORE_PATH,conf_paras))
        p.daemon = True
        process_list.append(p)

    delay=3
    for i in range(len(process_list)):
        process_list[i].start()
        print ("sleep %d seconds to enable next process"%(delay))
        time.sleep(delay)

    for i in range(len(process_list)):
        process_list[i].join()
    
    print ('begin to merge results')
    dict_merged={}
    list_allResult={}
    list_name=['pylucene']
       
    list_ext=['runs']
    for name in list_name:
        list_allResult[name]=[]
    
    for i in range(num_workers):
        for j in range(len(list_name)):
            name=list_name[j]
            filename=os.path.join(RES_STORE_PATH,name)+'_%s.%s'%(str(i),list_ext[j])
            with open(filename,'r',encoding='utf-8') as f_tmp:
                 list_allResult[name].extend(f_tmp.readlines())
            os.remove(filename)    

    list_allResult['pylucene'].sort(key=lambda item:item.split()[0],reverse=False)
    for j in range(len(list_name)):
        name=list_name[j]
        filename=os.path.join(RES_STORE_PATH,name)+'_all_mp.'+list_ext[j]
        with open(filename,'w',encoding='utf-8') as f:
             f.writelines(list_allResult[name])
              
    print ('total running time='+str((datetime.datetime.now() - starttime_total).seconds))
    
if __name__ == '__main__':
   conf_paras=Config_Object()
   main(conf_paras)
