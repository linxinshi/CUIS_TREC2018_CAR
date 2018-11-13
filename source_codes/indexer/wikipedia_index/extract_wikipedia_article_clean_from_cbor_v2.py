from urllib.request import unquote
from trec_car.read_data import *
from lib_process import *
import pymongo
import platform

from mongo_batch_object import Mongo_Batch_Object

# paragrapghID to article
# article to all its paragraphs
# article to its all sections


def traverse(v,depth,list_section):
    # v is a section of current article
    
    # process paragraphs
    list_avail_para=[]
    for para in v.children:
        try:
           para_id=para.paragraph.para_id
        except:
           continue
        text=para.paragraph.get_text()
        list_avail_para.append((para_id,text))
    
    flag_empty=True
    for section in v.child_sections:
        flag_empty_temp=traverse(section,depth+1,list_section)
        flag_empty=(flag_empty and flag_empty_temp)
    
    if flag_empty==True and len(list_avail_para)==0:
       pass
    else:
       list_section.append((v.heading,v.headingId,depth,list_avail_para))
    
    if len(list_avail_para)>0:
       return False
    else:
       return True    

def cleanText(text):
    text=text.replace('Category:',' ')
    text=stemSentence(remove_stopwords(cleanSentence(text,True)),None,False)
    return text

def main():
    if platform.system()=='Windows':
       port=27017
    else:
       port=58903
    client = pymongo.MongoClient('localhost',port)
    db=client.trec2017
    #conn_la=db['long_abstracts']
    
    conn_was=db['wiki_article_with_section_clean_stemmed_v2']
    conn_wasp=db['wiki_article_section_paragraph_v2']
    

    files = ['unprocessed.train.cbor']       
    cnt_debug=0
    
    batch_obj_was=Mongo_Batch_Object()
    batch_obj_wasp=Mongo_Batch_Object()    
    
    for item in files:
        with open(item, 'rb') as f:
             for p in iter_pages(f):
                 cnt_debug+=1
                 #if cnt_debug>30:
                    #break
                 if cnt_debug%10000==0:
                    print ('%d processed'%(cnt_debug))
                    
                 title=p.page_name.replace(' ','_')
                 
                 '''
                 item=conn_la.find_one({'title':title})
                 if item is None:
                    continue
                 '''
                 '''
                 print ('------------------------')
                 print('page_name:%s'%(p.page_name))
                 print('page_id:%s'%(p.page_id))
                 print ('title:%s'%(title))
                 '''
                 #print (p.to_string())
                 #print (p.skeleton)
                 
                 list_root_para=[]
                 for child in p.skeleton:
                     if isinstance(child, Para)==True:
                        list_root_para.append((child.paragraph.para_id,child.paragraph.get_text()))
                 
                 list_section=[]
                 #list_section.append(('root','root',1,list_root_para))
                 
                 for section in p.child_sections:
                     traverse(section,2,list_section)                 
                 
                 article=''
                 for para_pair in list_root_para:
                     para_id=para_pair[0]
                     text=cleanText(para_pair[1])
                     article+='%s\t%s\n'%(para_id,text)                     
                 
                 for section_pair in list_section:
                     heading,headingId=section_pair[0],section_pair[1]
                     depth=section_pair[2]
                     list_para=section_pair[3]
                     article+=('='*depth+heading+'='*depth+'\n')
                     
                     for para_pair in list_para:
                         para_id=para_pair[0]
                         text=cleanText(para_pair[1])
                         article+='%s\t%s\n'%(para_id,text) 
                         batch_obj_wasp.insert({'id':p.page_id,'title':title,'section':heading,'paragraphID':para_id},conn_wasp)                         
                 #print (article)
                 batch_obj_was.insert({'id':p.page_id,'title':title,'article':article},conn_was)   
                 
    batch_obj_was.cleanInsert(conn_was)
    batch_obj_wasp.cleanInsert(conn_wasp)             
    client.close()
if __name__ == '__main__':
   main()