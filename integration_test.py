import sys, os, lucene

from search import SearchEngine
from query_generator import QueryGenerator
from index import IndexFiles
from org.apache.lucene.analysis.standard import StandardAnalyzer

lucene.initVM(vmargs=['-Djava.awt.headless=true'])

# Index generator
# TODO : Add variation generation to integration test
""" 
First we need to create an index which is searchable by the lucene
index. Relevant code in Index.py
{
  "id": "doc1",
  "contents": "contents of doc one.",
  "keywords": "Vaccine 1",
  "Disease": "Disease 1",
}
This is the structure of the json file
"""
IndexTest = IndexFiles("./IndexFiles.Index",StandardAnalyzer())
IndexTest.indexFolder("./test_data")
indexDir = IndexTest.getIndexDir()

# Query generator
"""
Using the user entered data, we generate queries which can be used
to return results from the lucene index. Relevant code in query_generator.py
"""
QueryGenTest = QueryGenerator(StandardAnalyzer(), use_synonyms=True)
boosting_tokens = {
                    "keywords":["love"],    
                    "subject1":["care"]
                }
query_string = "contents"
query = QueryGenTest.build_query(query_string, \
  boosting_tokens, "OR_QUERY", field="contents")

# Search Engine
"""
Using the generated indexes and queries previously, get results for the 
user query. Relevant code in search_engine.py
"""
SearchEngineTest = SearchEngine(indexDir, rerank=True)

hits = SearchEngineTest.search(query, \
        query_string=query_string, query_field="contents")
print("%s total matching documents." % len(hits))

for doc in hits:
    print("contents : " , doc[1], "\nscore : ", doc[0])