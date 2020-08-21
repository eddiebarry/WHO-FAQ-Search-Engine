import sys, os, lucene

from search import SearchEngine
from query_generator import QueryGenerator
from index import IndexFiles
from org.apache.lucene.analysis.standard import StandardAnalyzer

lucene.initVM(vmargs=['-Djava.awt.headless=true'])

# Index generator
IndexTest = IndexFiles("./IndexFiles.Index",StandardAnalyzer())
IndexTest.indexFolder("./test_data")
indexDir = IndexTest.getIndexDir()

# Query generator
QueryGenTest = QueryGenerator(StandardAnalyzer())
boosting_tokens = {
                    "keywords":"love",    
                    "subject1":"care"
                }
query_string = "contents"
query = QueryGenTest.build_query(query_string, boosting_tokens, "OR_QUERY")


# Search Engine
SearchEngineTest = SearchEngine(indexDir)

hits = SearchEngineTest.search(query)
search_docs  = hits.scoreDocs
print("%s total matching documents." % len(search_docs))

for scoreDoc in search_docs:
    doc = SearchEngineTest.return_doc(scoreDoc.doc)
    print("contents : " , doc.get("contents"), "\nscore : ", scoreDoc.score)