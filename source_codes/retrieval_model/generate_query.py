q=set()
with open('automatic.benchmarkY1test.cbor.hierarchical.qrels','r',encoding='utf-8') as f:
     for line in f:
         list_item=line.strip().split()
         q.add(list_item[0])

#for query in q:
    #print (query)         
q_list=list(q)
q_list.sort()
for query in q_list:
    print (query)
#print (len(q_list))