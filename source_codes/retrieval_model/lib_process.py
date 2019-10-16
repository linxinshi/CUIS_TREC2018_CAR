# -*- coding: utf-8 -*- 
import string, re, gzip
import pickle
import nltk, numpy
from nltk.stem.snowball import SnowballStemmer
from nltk.corpus import stopwords

import lucene
from org.apache.lucene.index import Term
from org.apache.lucene.search import TermQuery
    
    
tabin=[ord(ch) for ch in string.punctuation]
tabout=[' ' for i in range(len(tabin))]
trantab=dict(zip(tabin,tabout)) 

for ch in "–—。，、）（·！】【`‘’":
    trantab[ord(ch)]=' '
    
whitelist=set(['win','won','most','biggest','largest','fastest'])
blacklist=set(['give','also',' ','and','of','in','list'])
stop = set(stopwords.words('english'))
filter_list=(stop|blacklist)-whitelist
    
def findOneDBEntry(conn,condition_field,value,result_field):
    item=conn.find_one({condition_field:value})
    if item is None:
       return None
    return item[result_field]
    
def findAllDBEntry(conn,condition_field,value):
    list_doc=conn.find({condition_field:value})
    if list_doc is None:
       return None
    return list_doc  
    
def save_zipped_pickle(obj, filename, protocol=-1):
    with gzip.open(filename, 'wb') as f:
         pickle.dump(obj, f, protocol)
         
def load_zipped_pickle(filename):
    with gzip.open(filename, 'rb') as f:
         loaded_object = pickle.load(f)
         return loaded_object
         
def save_obj(obj,filename):
    with open(filename,'wb') as f:
         pickle.dump(obj,f,pickle.HIGHEST_PROTOCOL)

def load_obj(filename):
    with open(filename, 'rb') as f:
         return pickle.load(f)

def remove_stopwords(line,SEPERATE_CHAR=' '):
    line=line.strip()
    if len(line)==0:
       return ''
    list=line.split(SEPERATE_CHAR)
    res_list=[]
    res_list=[word for word in list if word not in filter_list]
    return SEPERATE_CHAR.join(res_list)


def cleanSentence(line,isLower=True,SEPERATE_CHAR=' '):
    if len(line)==0:
       return ''
    
    line = line.translate(trantab)
    if isLower==True:
       line=line.lower()
    line=SEPERATE_CHAR.join(line.split())
    return line

def stemSentence(line,stemmer=SnowballStemmer('english'),isCleanNeeded=True):
    if isCleanNeeded==True:
       line=cleanSentence(line,True)
    if stemmer is None:
       stemmer=SnowballStemmer('english')
    list=line.split(' ')
    stemlist=[stemmer.stem(word) for word in list]
    res=' '.join(stemlist)
    return res
    
def superCleanSentence(line):
    # lower clean stem stopword_removed     
    line = line.translate(trantab).lower()
    list_term=line.split(' ')
    stemmer=SnowballStemmer('english')
    stemlist=[stemmer.stem(word) for word in list_term]
    
    return ' '.join([word for word in list_term if word not in filter_list])   
    
def cleanSentence2(line,isLower=True,SEPERATE_CHAR=' '):
    if len(line)==0:
       return ''

    replace_punctuation = str.maketrans(string.punctuation, ' '*len(string.punctuation))
    line = line.translate(replace_punctuation)
    if isLower==True:
       line=line.lower()
    line=SEPERATE_CHAR.join(line.split())
    return line

def cleanRelation(line):
    # http:
    l=re.findall('[a-zA-Z][^A-Z]*',line)
    return ' '.join(l)
    
def cleanValue(line):
    # value or http:
    if line.find('http')!=-1:
       pos_head = line.find("resource/")+9
       return line[pos_head:]
    else:
       return line
    
def cleanDBpediaValue(line):
    # relation%%%%value$$$$relation%%%%value
    if len(line)==0:
       return ''
    l=line.split('$$$$')
    res=''
    for item in l:
        pair=item.split('%%%%') # relation value
        relation=pair[0]
        value=pair[1]
        res=res+'%s %s '%(cleanRelation(relation),cleanValue(value))
    return cleanSentence(res,True)

#def remove_duplicate(line):
    #l=list(set(line.split(' ')))
    #return ' '.join(l)
def remove_duplicate(line,SEPERATE_CHAR=' '):
    ltmp=line.split(SEPERATE_CHAR)
    l=list(set(ltmp))
    l.sort(key=ltmp.index)
    res=' '.join(l)
    return res

    
    