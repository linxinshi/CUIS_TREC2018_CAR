# -*- coding: utf-8 -*-
from config import *
import os

class Config_Object(object):

      system_flag=None    
      mongo_port=58903
      
      def __init__(self):
          self.system_flag=SYSTEM_FLAG
          self.LUCENE_INDEX_DIR=os.path.join('mmapDirectory','trec_v21_paragraph_stemmed_v2')
          #self.LUCENE_INDEX_DIR=os.path.join('mmapDirectory','corpus_2')
          self.LUCENE_INDEX_WIKI_DIR=os.path.join('mmapDirectory','trec_v21_wikipedia_stemmed_v2')
          self.LUCENE_INDEX_URI_DIR=os.path.join('mmapDirectory','trec_v21_para_uri')
          if TAXONOMY=='Wikipedia':
             self.LUCENE_INDEX_CATEGORY_CORPUS=os.path.join('mmapDirectory','category_para_corpus_trec2018_top5')
          
          
          self.QUERY_FILEPATH=os.path.join('queries-trec2018-official-v3.txt')
          self.PATH_GROUNDTRUTH=os.path.join('benchmarkY2test-psg-lenient.qrels')
          self.PATH_GROUNDTRUTH_MANUAL=os.path.join('benchmarkY2test-psg-manual.qrels')
          
          if TAXONOMY=='Wikipedia':
             self.PATH_CATEGORY_DAG='category_dag_dbpedia_top10.pkl.gz'
          
          if self.system_flag=='Windows':
             self.LUCENE_INDEX_DIR=os.path.join('H:\\',self.LUCENE_INDEX_DIR)
             self.LUCENE_INDEX_WIKI_DIR=os.path.join('H:\\',self.LUCENE_INDEX_WIKI_DIR)
             self.LUCENE_INDEX_CATEGORY_CORPUS=os.path.join('G:\\',self.LUCENE_INDEX_CATEGORY_CORPUS)
             self.LUCENE_INDEX_URI_DIR=os.path.join('G:\\',self.LUCENE_INDEX_URI_DIR)
            
             self.mongo_port=27017
             if TAXONOMY=='Wikipedia':
                self.PATH_CATEGORY_DAG=os.path.join('F:\\','研究数据','Wikipedia_DBpedia_data','DBpedia_data','2015-10','category_structure_processing',self.PATH_CATEGORY_DAG)
