import math
from config import *
from lib_process import findOneDBEntry
from list_term_object import List_Term_Object

def get_dirichlet_prob(tf_t_d, len_d, tf_t_C, len_C, mu):
    """
    Computes Dirichlet-smoothed probability
    P(t|theta_d) = [tf(t, d) + mu P(t|C)] / [|d| + mu]

    :param tf_t_d: tf(t,d)
    :param len_d: |d|
    :param tf_t_C: tf(t,C)
    :param len_C: |C| = \sum_{d \in C} |d|
    :param mu: \mu
    :return:
    """
    if mu == 0:  # i.e. field does not have any content in the collection
       return 0
    else:
       p_t_C = tf_t_C / len_C if len_C > 0.0 else 0.0
       return (tf_t_d + mu * p_t_C) / (len_d + mu)

       
       
def elrSim(queryObj,paraObj,lucene_obj,mongoObj):
    # only catchall field
    field='entities'
    #df_f=lucene_obj.get_doc_count(field)
    score=NEGATIVE_INFINITY
    
    # get para entities
    d,docID=lucene_obj.findDoc(paraObj.para_id,'id',True)
    if d is None or docID is None:
       return 0.0
       
    term_freq=lucene_obj.get_term_freq(docID,field,False)
    
    # for Dir
    len_d=sum(term_freq.values())
    len_C_f = lucene_obj.get_coll_length(field)
    mu=lucene_obj.get_avg_len(field)
    
    for entity in queryObj.query_entities:
        se=queryObj.query_entities[entity]
        
        #tf=1 if entity in term_freq else 0
        tf=term_freq.get(entity,0)
        #df_e_f=lucene_obj.get_doc_freq(entity, field)
        
        cf = lucene_obj.get_coll_termfreq(entity, field)

        cur_score=NEGATIVE_INFINITY
        ptc=cf/len_C_f if len_C_f>0 else 0.0
        sim=(tf+mu*ptc)/(len_d+mu)
        #sim=0.9*tf+0.1*(df_e_f/df_f)
        
        if sim>0:
           cur_score=se*math.log(sim)
        if cur_score>score:
           score=cur_score
           
    if score==NEGATIVE_INFINITY:
       return 0.0
    else:
       #print ('score=%f'%(score))
       return score
    
def bm25fSim(lt_obj1,paraObj,lucene_obj):
    len_C_f={}
    mu={}
    for f in LIST_F:
        len_C_f[f]=lucene_obj.get_coll_length(f)
        mu[f]=lucene_obj.get_avg_len(f)
        
    N=lucene_obj.get_doc_count('stemmed_catchall')    
    k1=2.44
    b=0.297
    boost=1
    
    totalSim=0.0
    for i in range(lt_obj1.length):
        term=lt_obj1.term[i]
        localSim=0.0
        df_t=lucene_obj.get_doc_freq(term,'stemmed_catchall')
        idf_t=math.log10((N-df_t+0.5)/(df_t+0.5))
        weight_t_d=0.0
        
        for f in LIST_F:
            len_d_f = paraObj.lengths[f]
            tf_t_d_f = paraObj.term_freqs[f].get(term,0)
            tf_t_C_f = lucene_obj.get_coll_termfreq(term, f)
            
            # compute f(p(t1|De),p(t2|De)...) 
            weight_t_d+=((tf_t_d_f*boost)/(1-b+b*(len_d_f/mu[f])))
        totalSim+=(idf_t*(weight_t_d/(k1+weight_t_d)))    
    return totalSim
 
def lmSim(lt_obj1,paraObj,field,lucene_obj,mongoObj=None):
    # subquery x et[0..n-1] 
    totalSim=0.0
    term_freq=paraObj.term_freq
    len_C_f = lucene_obj.get_coll_length(field)
    mu=lucene_obj.get_avg_len(field)
    
    # iterate each t in term_freq and compare similarity
    for i in range(lt_obj1.length):
        qt=lt_obj1.term[i]
        localSim=0.0
        # compute p(t|De)
        if qt in term_freq:
           localSim=term_freq[qt]
                    
        len_d_f = paraObj.length
        tf_t_d_f = localSim
        tf_t_C_f = lucene_obj.get_coll_termfreq(qt, field)
        
        p_t_d=get_dirichlet_prob(tf_t_d_f, float(len_d_f), float(tf_t_C_f), float(len_C_f), mu)
        # compute f(p(t1|De),p(t2|De)...) 
        if p_t_d>0.0:
           totalSim+=math.log(p_t_d)
    return totalSim
    

def sdmSim(queryObj,paraObj,field,lucene_obj):
    ft=fo=fu=0.0
    len_C_f = lucene_obj.get_coll_length(field)
    mu=lucene_obj.get_avg_len(field)
    
    ft=lmSim(queryObj.contents_obj,paraObj,field,lucene_obj)
    if LAMBDA_O>0:
       for bigram_pair in queryObj.bigrams:
           bigram=bigram_pair[0]+' '+bigram_pair[1]
           tf,cf=lucene_obj.get_coll_bigram_freq(bigram,field,True,0,paraObj.id,'id')
           ptd=get_dirichlet_prob(tf,paraObj.length,cf,len_C_f,mu)
           if ptd>0:
              fo+=math.log(ptd)
    if LAMBDA_U>0:
       for bigram_pair in queryObj.bigrams:
           bigram=bigram_pair[0]+' '+bigram_pair[1]
           tf,cf=lucene_obj.get_coll_bigram_freq(bigram,field,False,6,paraObj.id,'id')
           ptd=get_dirichlet_prob(tf,paraObj.length,cf,len_C_f,mu)
           if ptd>0:
              fu+=math.log(ptd)
    score=LAMBDA_T*ft+LAMBDA_O*fo+LAMBDA_U*fu
    return score

def sdm_sas2(queryObj,paraObj,structure,lucene_handler):
    if len(paraObj.categories)==0:
       return NEGATIVE_INFINITY
    D=structure.cat_dag
    lucene_cat=lucene_handler['category_corpus']
    lucene_doc=lucene_handler['first_pass']
    
    len_d=paraObj.length
    
    sum_score=0.0
    max_score=NEGATIVE_INFINITY
    
    # prepare field weights
    f=USED_CONTENT_FIELD
    len_C_f=lucene_doc.get_coll_length(f)
    mu=lucene_doc.get_avg_len(f)
        
    def smooth_path(cat,path_len):
        nonlocal D,cnt_path
        nonlocal num_articles_g,len_c_g,cf_g
        nonlocal lucene_cat,lucene_doc
        
        if cnt_path>TOP_PATH_NUM_PER_CAT:
           return
        # the following is end condition
        if path_len==LIMIT_SAS_PATH_LENGTH or len(D[cat])==0:
           # compute score
           cnt_path+=1
           return
           
        # maintain useful temporary variables
        # current node is cat
        cat_corpus,docID=lucene_cat.findDoc(cat,'category',True)
        if cat_corpus is not None:
           # maintain
           cnt_doc_corpus=int(cat_corpus['num_paras'])
           num_articles_g+=cnt_doc_corpus
           # get category corpus
           term_freq_c=lucene_cat.get_term_freq(docID,f,True)
           len_c=sum(term_freq_c.values())
           len_c_g+=len_c           
           # maintain individual query terms
           for j in range(queryObj.contents_obj.length):
               term=queryObj.contents_obj.term[j]
               cf_g[('T',j)]=term_freq_c.get(term,0.0)           
           # maintain ordered bigrams
           if LAMBDA_O>0:
              for j in range(len(queryObj.bigrams)):
                  bigram=queryObj.bigrams[j][0]+' '+queryObj.bigrams[j][1]
                  cf_c,cf_cc=lucene_cat.get_coll_bigram_freq(bigram,f,True,0,cat,field_cache='category')
                  cf_g[('O',j)]=cf_c
           # maintain unordered bigrams
           if LAMBDA_U>0:
              for j in range(len(queryObj.bigrams)):
                  bigram=queryObj.bigrams[j][0]+' '+queryObj.bigrams[j][1]
                  cf_c,cf_cc=lucene_cat.get_coll_bigram_freq(bigram,f,False,6,cat,field_cache='category')
                  cf_g[('U',j)]=cf_c             
        cnt=0
        for child in iter(D[cat]):
            cnt+=1
            if cnt>TOP_CATEGORY_NUM:
               break
            if child in D:
               smooth_path(child,path_len+1)
    # end of function smooth_path
    
    for cat in paraObj.categories[:TOP_CATEGORY_NUM]:
        if cat not in D:
           continue
        max_score_p_cat=NEGATIVE_INFINITY     
        cnt_path=0
        
        num_articles_g=0
        len_c_g=0
        cf_g={} # cf_g[('T',j)]
        
        smooth_path(cat,1)
        
        cof,score_p=0.01,0.0
        ft_p,fo_p,fu_p=0.0,0.0,0.0
        mu_g=len_c_g/num_articles_g if num_articles_g>0 else 0.0
        
        for j in range(queryObj.contents_obj.length):
            term=queryObj.contents_obj.term[j]
            ptd=0.0
            tf_d=paraObj.term_freq.get(term,0.0)
            cf=lucene_doc.get_coll_termfreq(term, f)
            ptc=cf/len_C_f if len_C_f>0 else 0.0
            ptc_g=cf_g[('T',j)]/len_c_g if len_c_g>0 else 0.0
            Dt=mu*ptc+cof*mu_g*ptc_g
            Nt=mu+cof*mu_g
            ptd=(tf_d+Dt)/(len_d+Nt) if len_d+Nt>0 else 0.0
            if ptd>0:
               ft_p+=math.log(ptd)
        # for ordered bigrams
        if LAMBDA_O>0:
           for j in range(len(queryObj.bigrams)):
               bigram=queryObj.bigrams[j][0]+' '+queryObj.bigrams[j][1]
               ptd=0.0
               tf_d,cf=lucene_doc.get_coll_bigram_freq(bigram,f,True,0,paraObj.id)
               ptc=cf/len_C_f if len_C_f>0 else 0.0
               ptc_g=cf_g[('O',j)]/len_c_g if len_c_g>0 else 0.0
               Dt=mu*ptc+cof*mu_g*ptc_g
               Nt=mu+cof*mu_g
               #Dt=mu*ptc
               #Nt=mu
               ptd=(tf_d+Dt)/(len_d+Nt) if len_d+Nt>0 else 0.0
               if ptd>0:
                  fo_p+=math.log(ptd)          
        # for unordered bigrams
        if LAMBDA_U>0:
           for j in range(len(queryObj.bigrams)):
               bigram=queryObj.bigrams[j][0]+' '+queryObj.bigrams[j][1]
               ptd=0.0
               tf_d,cf=lucene_doc.get_coll_bigram_freq(bigram,f,False,6,paraObj.id)
               ptc=cf/len_C_f if len_C_f>0 else 0.0
               ptc_g=cf_g[('U',j)]/len_c_g if len_c_g>0 else 0.0
               Dt=mu*ptc+cof*mu_g*ptc_g
               Nt=mu+cof*mu_g
               #Dt=mu*ptc
               #Nt=mu
               ptd=(tf_d+Dt)/(len_d+Nt) if len_d+Nt>0 else 0.0
               if ptd>0:
                  fu_p+=math.log(ptd)         
        # end computing feature function
        score_p=LAMBDA_T*ft_p+LAMBDA_O*fo_p+LAMBDA_U*fu_p
        if score_p>max_score_p_cat:
           max_score_p_cat=score_p        
         
        if max_score_p_cat>NEGATIVE_INFINITY:
           sum_score+=max_score_p_cat
        if max_score_p_cat>max_score:
           max_score=max_score_p_cat
               
    return max_score
    
def sdm_sas(queryObj,paraObj,structure,lucene_handler):
    if len(paraObj.categories)==0:
       return NEGATIVE_INFINITY
    D=structure.cat_dag
    lucene_cat=lucene_handler['category_corpus']
    lucene_doc=lucene_handler['first_pass']
    
    len_d=paraObj.length
    
    sum_score=0.0
    max_score=NEGATIVE_INFINITY
    len_C_f={}
    sum_ptc={}
    mu={}
    
    # prepare field weights
        
    for field in LIST_F:
        len_C_f[field]=lucene_doc.get_coll_length(field)
        mu[field]=lucene_doc.get_avg_len(field)
        sum_ptc[('T',field)]=[0.0 for i in range(queryObj.contents_obj.length)]
        sum_ptc[('O',field)]=[0.0 for i in range(len(queryObj.bigrams))]
        sum_ptc[('U',field)]=[0.0 for i in range(len(queryObj.bigrams))]
        
    curPath=[]

    def smooth_path(cat,path_len,alpha_t,sum_nominator):
        nonlocal D,curPath,sum_ptc,cnt_path
        nonlocal max_score_p_cat,max_score
        nonlocal lucene_cat,lucene_doc
        
        if cnt_path>TOP_PATH_NUM_PER_CAT:
           return
        # the following is end condition
        if path_len==LIMIT_SAS_PATH_LENGTH or len(D[cat])==0:
           # compute score
           cnt_path+=1
           if alpha_t==ALPHA_SAS:
              return           
           # TAKE CARE OF COF !
           #cof=(1-ALPHA_SAS)/(ALPHA_SAS-alpha_t)
           #cof=0.01
           cof=1/7000
           score_p=0.0
           # for individual query terms
           ft_p=0.0
           for j in range(queryObj.contents_obj.length):
               term=queryObj.contents_obj.term[j]
               ptd=0.0
               f=USED_CONTENT_FIELD
               tf_d_f=paraObj.term_freq.get(term,0.0)
               cf_f = lucene_doc.get_coll_termfreq(term, f)
               ptc_f=cf_f/len_C_f[f] if len_C_f[f]>0 else 0.0
               Dt=mu[f]*ptc_f
               Nt=mu[f]
               Dt+=cof*sum_ptc[('T',f)][j]
               Nt+=cof*sum_nominator[f]
               ptd=(tf_d_f+Dt)/(len_d+Nt) if len_d+Nt>0 else 0.0
               if ptd>0:
                  ft_p+=math.log(ptd)
           # for ordered bigrams
           fo_p=0.0
           if LAMBDA_O>0:
              for j in range(len(queryObj.bigrams)):
                  bigram=queryObj.bigrams[j][0]+' '+queryObj.bigrams[j][1]
                  ptd=0.0
                  f=USED_CONTENT_FIELD
                  tf_d_f,cf_f=lucene_doc.get_coll_bigram_freq(bigram,f,True,0,paraObj.id)
                  ptc_f=cf_f/len_C_f[f] if len_C_f[f]>0 else 0.0
                  Dt=mu[f]*ptc_f
                  Nt=mu[f]
                  Dt+=cof*sum_ptc[('O',f)][j]
                  Nt+=cof*sum_nominator[f]
                  ptd=(tf_d_f+Dt)/(len_d+Nt) if len_d+Nt>0 else 0.0
                  if ptd>0:
                     fo_p+=math.log(ptd)          
           # for unordered bigrams
           fu_p=0.0
           if LAMBDA_U>0:
              for j in range(len(queryObj.bigrams)):
                  bigram=queryObj.bigrams[j][0]+' '+queryObj.bigrams[j][1]
                  ptd=0.0
                  f=USED_CONTENT_FIELD
                  tf_d_f,cf_f=lucene_doc.get_coll_bigram_freq(bigram,f,False,6,paraObj.id)
                  ptc_f=cf_f/len_C_f[f] if len_C_f[f]>0 else 0.0
                  Dt=mu[f]*ptc_f
                  Nt=mu[f]
                  Dt+=cof*sum_ptc[('U',f)][j]
                  Nt+=cof*sum_nominator[f]
                  ptd=(tf_d_f+Dt)/(len_d+Nt) if len_d+Nt>0 else 0.0
                  if ptd>0:
                     fu_p+=math.log(ptd)         
           # end computing feature function
           score_p=LAMBDA_T*ft_p+LAMBDA_O*fo_p+LAMBDA_U*fu_p
           if score_p>max_score_p_cat:
              max_score_p_cat=score_p
           return
           
        # maintain useful temporary variables
        # current node is cat
        cat_corpus,docID=lucene_cat.findDoc(cat,'category',True)
        bak_sum_ptc=sum_ptc.copy()
        if cat_corpus is not None:
           # maintain
           cnt_doc_corpus=int(cat_corpus['num_paras'])
           for f in LIST_F:
               # get category corpus
               term_freq_c=lucene_cat.get_term_freq(docID,f,True)
               len_c=sum(term_freq_c.values())
               mu_c=len_c/cnt_doc_corpus if cnt_doc_corpus>0 else 0.0
               sum_nominator[f]+=alpha_t*mu_c       
               # maintain individual query terms
               for j in range(queryObj.contents_obj.length):
                   term=queryObj.contents_obj.term[j]
                   cf_c=term_freq_c.get(term,0.0)     
                   ptc_f=cf_c/len_c if len_c>0 else -1    
                   if ptc_f>-1:  
                      sum_ptc[('T',f)][j]+=(alpha_t*ptc_f*mu_c)                     
               # maintain ordered bigrams
               if LAMBDA_O>0:
                  for j in range(len(queryObj.bigrams)):
                      bigram=queryObj.bigrams[j][0]+' '+queryObj.bigrams[j][1]
                      cf_c,cf_cc=lucene_cat.get_coll_bigram_freq(bigram,f,True,0,cat,field_cache='category')
                      ptc_f=cf_c/len_c if len_c>0 else -1
                      if ptc_f>-1:
                         sum_ptc[('O',f)][j]+=(alpha_t*ptc_f*mu_c)
               # maintain unordered bigrams
               if LAMBDA_U>0:
                  for j in range(len(queryObj.bigrams)):
                      bigram=queryObj.bigrams[j][0]+' '+queryObj.bigrams[j][1]
                      cf_c,cf_cc=lucene_cat.get_coll_bigram_freq(bigram,f,False,6,cat,field_cache='category')
                      ptc_f=cf_c/len_c if len_c>0 else -1
                      if ptc_f>-1:
                         sum_ptc[('U',f)][j]+=(alpha_t*ptc_f*mu_c)               
        cnt=0
        for child in iter(D[cat]):
            cnt+=1
            if cnt>TOP_CATEGORY_NUM:
               break
            if child in D:
               curPath.append(child)
               smooth_path(child,path_len+1,alpha_t*ALPHA_SAS,sum_nominator)
               curPath.pop()
               sum_ptc=bak_sum_ptc.copy()
    # end of function smooth_path
    
    for cat in paraObj.categories[:TOP_CATEGORY_NUM]:
        if cat not in D:
           continue
        max_score_p_cat=NEGATIVE_INFINITY     
        cnt_path=0
        smooth_path(cat,1,ALPHA_SAS,{f:0.0 for f in LIST_F})
        
        if max_score_p_cat>NEGATIVE_INFINITY:
           sum_score+=max_score_p_cat
        if max_score_p_cat>max_score:
           max_score=max_score_p_cat
               
    return max_score

    

#===========================================
def lm_sas(queryObj,paraObj,structure,lucene_handler,mongoObj,field):
    if len(paraObj.categories)==0:
       return NEGATIVE_INFINITY
    D=structure.cat_dag
    lucene_cat=lucene_handler['category_corpus']
    lucene_doc=lucene_handler['first_pass']
    
    termList=paraObj.term_freq
    len_d=paraObj.length
    
    sum_score=0.0
    max_score=NEGATIVE_INFINITY
    len_C_f = lucene_doc.get_coll_length(field)
    mu_d=lucene_doc.get_avg_len(field)

    curPath=[]
    sum_ptc=[0.0 for i in range(queryObj.contents_obj.length)]
    
    def smooth_path(cat,path_len,alpha_t,sum_nominator):
        nonlocal D,curPath,sum_ptc,cnt_path
        nonlocal max_score_p_cat,max_score
        nonlocal lucene_cat,lucene_doc
        
        #print (cat)
        if cnt_path>TOP_PATH_NUM_PER_CAT:
           return
        if path_len==LIMIT_SAS_PATH_LENGTH or len(D[cat])==0:
           # compute score
           cnt_path+=1
           if alpha_t==ALPHA_SAS:
              return       
           cof=(1-ALPHA_SAS)/(ALPHA_SAS-alpha_t)
           #cof=0.003
           #cof=1
           #cof=0.3
           # 0.3 for DBpedia
           score_p=0.0
           for j in range(queryObj.contents_obj.length):
                term=queryObj.contents_obj.term[j]
                tf_d=paraObj.term_freq.get(term,0.0)
                tf_t_C_f = lucene_doc.get_coll_termfreq(term, field)
                ptc_doc=tf_t_C_f/len_C_f if len_C_f>0 else 0.0
                ptd=(tf_d+mu_d*ptc_doc+cof*sum_ptc[j])/(len_d+mu_d+cof*sum_nominator) if len_d+mu_d+cof*sum_nominator>0 else 0.0
                #print ('%s\t%f\t%f'%(term,sum_ptc[j],sum_nominator))
                '''
                if tf_d>0 and sum_ptc[j]>0:
                   ptd=(tf_d+mu_d*ptc_doc+cof*sum_ptc[j])/(len_d+mu_d+cof*sum_nominator) if len_d+mu_d+cof*sum_nominator>0 else 0.0
                else:
                   ptd=(tf_d+mu_d*ptc_doc)/(len_d+mu_d) if len_d+mu_d>0 else 0.0
                   #ptd=0 will impact performance for lm on all datasets
                '''
                if ptd>0:
                   score_p+=math.log(ptd)
           if score_p>max_score_p_cat:
              max_score_p_cat=score_p
           return
           
        # maintain useful temporary variables
        d,docID=lucene_cat.findDoc(cat,'category',True)
        bak_sum_ptc=sum_ptc[:]
        if d is not None:
           # maintain
           
           term_freq=lucene_cat.get_term_freq(docID,field,True)
           len_c=sum(term_freq.values())
           cnt_doc_corpus=int(d['num_articles'])
           mu_c=len_c/cnt_doc_corpus if cnt_doc_corpus>0 else 0.0
           sum_nominator+=alpha_t*mu_c         

           #print ('find %s, len_c=%d, mu_c=%f'%(cat,len_c,mu_c))
           
           for j in range(queryObj.contents_obj.length):
               term=queryObj.contents_obj.term[j]
               tf_c=term_freq.get(term,0.0)     
               ptc=tf_c/len_c if len_c>0 else -1    
               if ptc>-1:  
                  sum_ptc[j]+=(alpha_t*ptc*mu_c)                     
        cnt=0
        for child in iter(D[cat]):
            cnt+=1
            if cnt>TOP_CATEGORY_NUM:
               break
            if child in D:
               curPath.append(child)
               smooth_path(child,path_len+1,alpha_t*ALPHA_SAS,sum_nominator)
               curPath.pop()
               sum_ptc=bak_sum_ptc[:]
    # end of function smooth_path
      
    for cat in paraObj.categories[:TOP_CATEGORY_NUM]:
        #print (cat)
        if cat not in D:
           #print ('%s not in D'%(cat))
           continue
        #print ('---')
        max_score_p_cat=NEGATIVE_INFINITY     
        cnt_path=0
        #smooth_path(cat,1,1.0,0.0)
        smooth_path(cat,1,ALPHA_SAS,0.0)
        if max_score_p_cat>NEGATIVE_INFINITY:
           sum_score+=max_score_p_cat
        if max_score_p_cat>max_score:
           max_score=max_score_p_cat
        #print (max_score_p_cat)
        #print ('cnt_path=%d'%(cnt_path))           
    return max_score

# ============================
def scoreWikiTree(queryObj,T_obj,lucene_obj,field):
    curPath=[]
    bestPath=[]
    maxScore=NEGATIVE_INFINITY
    T=T_obj.T
    mu=lucene_obj.get_avg_len(field)
    len_C = lucene_obj.get_coll_length(field)
    sum_w_tf_ug=[0.0 for i in range(queryObj.contents_obj.length)]
    sum_w_tf_ob=[0.0 for i in range(len(queryObj.bigrams))]
    sum_w_tf_ub=[0.0 for i in range(len(queryObj.bigrams))]  
    
    def scorePath(v,sum_w_len,len_path):
        # v:node sum_w_tf:sum of weighted tf, sum_w_len:sum of weighted doc len
        nonlocal T_obj,T,lucene_obj,queryObj
        nonlocal field,maxScore
        nonlocal curPath,bestPath,sum_w_tf_ug,sum_w_tf_ob,sum_w_tf_ub
        # slow  revise traverse
        
        if v==-1 or len_path>LIMIT_D_PATH_LENGTH:
           score_T=score_U=score_O=0.0
           for i in range(queryObj.contents_obj.length):
               term=queryObj.contents_obj.term[i]
               cf=lucene_obj.get_coll_termfreq(term,field)
               score_i=get_dirichlet_prob(sum_w_tf_ug[i], sum_w_len, cf, len_C, mu)
               if score_i>0:
                  score_T+=math.log(score_i)
           for i in range(len(queryObj.bigrams)):
               bigram=queryObj.bigrams[i][0]+' '+queryObj.bigrams[i][1]
               cf=lucene_obj.get_coll_bigram_freq(bigram,field,True,0,T_obj.title,'title')[1]
               score_i=get_dirichlet_prob(sum_w_tf_ob[i], sum_w_len, cf, len_C, mu)
               if score_i>0:
                  score_O+=math.log(score_i)
                  
           for i in range(len(queryObj.bigrams)):
               bigram=queryObj.bigrams[i][0]+' '+queryObj.bigrams[i][1]
               cf=lucene_obj.get_coll_bigram_freq(bigram,field,False,6,T_obj.title,'title')[1]
               score_i=get_dirichlet_prob(sum_w_tf_ub[i], sum_w_len, cf, len_C, mu)
               if score_i>0:
                  score_U+=math.log(score_i)   
           score=LAMBDA_T*score_T+LAMBDA_O*score_O+LAMBDA_U*score_U
           if score==0:
              score=NEGATIVE_INFINITY           
           if score>maxScore:
              maxScore=score
              bestPath=curPath.copy()
        else:
           content=' '.join(T[v][field])
           T[v]['list_term_object']=List_Term_Object(content,True,' ',None,is_bigram_used=True)
           lto=T[v]['list_term_object']
           bak_ug=sum_w_tf_ug.copy()
           bak_ob=sum_w_tf_ob.copy()
           bak_ub=sum_w_tf_ub.copy()
           
           for i in range(queryObj.contents_obj.length):
               term=queryObj.contents_obj.term[i]
               tf=lto.term_freq.get(term,0)
               sum_w_tf_ug[i]=sum_w_tf_ug[i]*ALPHA_D+tf
           for i in range(len(queryObj.bigrams)):
               bigram=queryObj.bigrams[i][0]+' '+queryObj.bigrams[i][1]
               tf=lto.bigram_freq.get(bigram,0)
               sum_w_tf_ob[i]=sum_w_tf_ob[i]*ALPHA_D+tf
           for i in range(len(queryObj.bigrams)):
               bigram=queryObj.bigrams[i]
               term1,term2=bigram
               p2=tf=0
               # can be optimized via suffix array
               for p1 in range(queryObj.contents_obj.length):
                   if queryObj.contents_obj.term[p1] not in [term1,term2]:
                      continue
                   for p2 in range(p1+1,queryObj.contents_obj.length):
                       if p2-p1-1>6:
                          break
                       elif queryObj.contents_obj.term[p2] in [term1,term2]:
                            tf+=1     
               sum_w_tf_ub[i]=sum_w_tf_ub[i]*ALPHA_D+tf  
               
           if len(T[v]['child'])>0:
              for c in T[v]['child']:
                  scorePath(c,sum_w_len*ALPHA_D+lto.length,len_path+1)
           else:
              scorePath(-1,sum_w_len*ALPHA_D+lto.length,len_path+1)
           sum_w_tf_ug=bak_ug.copy()
           sum_w_tf_ob=bak_ob.copy()
           sum_w_tf_ub=bak_ub.copy()
    # ----------------------------------------------------    
    for v in T[1]['child']:    
        sum_w_tf_ug=[0.0 for i in range(queryObj.contents_obj.length)]
        sum_w_tf_ob=[0.0 for i in range(len(queryObj.bigrams))]
        sum_w_tf_ub=[0.0 for i in range(len(queryObj.bigrams))]    
        scorePath(v,0.0,0)
    return maxScore

        