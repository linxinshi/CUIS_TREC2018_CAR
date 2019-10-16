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

          self.QUERY_FILEPATH=os.path.join('queries-trec2018-official-v3.txt')
          self.PATH_GROUNDTRUTH=os.path.join('benchmarkY2test-psg-lenient.qrels')
          self.PATH_GROUNDTRUTH_MANUAL=os.path.join('benchmarkY2test-psg-manual.qrels')
          
