# coding=utf-8
# global parameter
import platform

SYSTEM_FLAG=platform.system()
DATA_VERSION = 2018
hitsPerPage = 1000
NUM_PROCESS= 4
FROM_INDEX=0
FROM_DB=1
SEPERATE_CHAR_SUBQUERY='|'
CHOICE_WEIGHT='weight' # 'weight' or 'similarity'

NEGATIVE_INFINITY=-99999999
QUERY_EXPANSION_LEVEL=3

MODEL_NAME='sdm'
RUN_NAME='CUIS'
IS_WIKI_DOC_TREE_USED=False # for wiki doc tree
IS_SAS_USED=False
IS_ELR_USED=False
QUERY_ENTITY_COLLECTION='query_entities_2018'

BOUND_SIM=0.97

# for bigram related operation
IS_BIGRAM_CACHE_USED=False
if MODEL_NAME.find('sdm')>-1:
   IS_BIGRAM_CACHE_USED=True

# for FSDM model
LAMBDA_T=0.8
LAMBDA_O=0.1
LAMBDA_U=0.1

# for structure-aware smoothing
SAS_MAX_ARTICLE_PER_CAT=100
SAS_MODE='BOTTOMUP'
TAXONOMY='Wikipedia'  # Wikipedia or DBpedia
LIMIT_SAS_PATH_LENGTH=2
# 10,20
TOP_CATEGORY_NUM=5
# 30
TOP_PATH_NUM_PER_CAT=100
ALPHA_SAS=0.75

# for doc smoothing
LIMIT_D_PATH_LENGTH=10
ALPHA_D=0.8

# for Query_Object
USED_QUERY_VERSION='stemmed_raw_query'
IS_STOPWORD_REMOVED=True
IS_SUBQUERY_USED=False
# corpus_2:stemmed_contents  trec_v15:stemmed_catchall
#USED_CONTENT_FIELD='stemmed_contents' 
USED_CONTENT_FIELD='stemmed_catchall' 
LIST_F=[USED_CONTENT_FIELD]
NO_SMOOTHING_LIST=[]