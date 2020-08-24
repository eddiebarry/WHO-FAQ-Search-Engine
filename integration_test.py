import sys, os, lucene

from search import SearchEngine
from query_generator import QueryGenerator
from index import IndexFiles
from org.apache.lucene.analysis.standard import StandardAnalyzer

lucene.initVM(vmargs=['-Djava.awt.headless=true'])

# Index generator
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
QueryGenTest = QueryGenerator(StandardAnalyzer())
boosting_tokens = {
                    "keywords":"love",    
                    "subject1":"care"
                }
query_string = "contents"
query = QueryGenTest.build_query(query_string, boosting_tokens, "OR_QUERY")


# Search Engine
"""
Using the generated indexes and queries previously, get results for the 
user query. Relevant code in search_engine.py
"""
SearchEngineTest = SearchEngine(indexDir)

hits = SearchEngineTest.search(query)
search_docs  = hits.scoreDocs
print("%s total matching documents." % len(search_docs))

for scoreDoc in search_docs:
    doc = SearchEngineTest.return_doc(scoreDoc.doc)
    print("contents : " , doc.get("contents"), "\nscore : ", scoreDoc.score)