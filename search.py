#!/usr/bin/env python

import sys, os, lucene

from java.nio.file import Paths
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.index import DirectoryReader
from org.apache.lucene.queryparser.classic import QueryParser
from org.apache.lucene.store import SimpleFSDirectory
from org.apache.lucene.search import IndexSearcher


# TODO document
class SearchEngine:
    
    def __init__(self, index_dir):
        self.directory = \
            SimpleFSDirectory(Paths.get(index_dir))
        self.searcher = \
            IndexSearcher(DirectoryReader.open(self.directory))
        self.analyzer = StandardAnalyzer()
    
    def update(self, new_dir):
        self.directory = \
            SimpleFSDirectory(Paths.get(new_dir))
        self.searcher = \
            IndexSearcher(DirectoryReader.open(directory))
        self.analyzer = StandardAnalyzer()
    
    def search(self, query, top_n=50):
        scoreDocs = self.searcher.search(query, top_n)
        return scoreDocs
        # jsonDocs = self.convert_to_json(scoreDocs)
        # return jsonDocs
    
    def return_doc(self,doc_id):
        return self.searcher.doc(doc_id)

    def convert_to_json(self, scoreDocs):
        pass

if __name__ == '__main__':

    lucene.initVM(vmargs=['-Djava.awt.headless=true'])
    # Search Engine
    indexDir = "./IndexFiles.Index"
    SearchEngineTest = SearchEngine(indexDir)
    

    query_string = "contents of"
    query = QueryParser("contents", StandardAnalyzer() ).parse(query_string)
    
    hits = SearchEngineTest.search(query)
    search_docs  = hits.scoreDocs
    print("%s total matching documents." % len(search_docs))

    for scoreDoc in search_docs:
        doc = SearchEngineTest.return_doc(scoreDoc.doc)
        print("contents : " , doc.get("contents"), "\nscore : ", scoreDoc.score)