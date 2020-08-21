#!/usr/bin/env python

import sys, os, lucene

from java.nio.file import Paths
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.index import DirectoryReader
from org.apache.lucene.queryparser.classic import QueryParser
from org.apache.lucene.store import SimpleFSDirectory
from org.apache.lucene.search import IndexSearcher

class QueryGenerator:
    def __init__(self, analyzer):
        self.analyzer = analyzer
    
    def build_query(self, query_string, boosting_tokens, query_type):
        if query_type == "OR_QUERY":
            query_string = \
                self.get_or_query_string(query_string, \
                boosting_tokens, boost_val=1.05)

        query = QueryParser("contents", self.analyzer).parse(query_string)
        
        return query

    def get_or_query_string(self, query_string, boosting_tokens, boost_val):
        if boost_val:
            boost_string = ""
            for x in boosting_tokens:
                boost_string = boost_string + " OR " + \
                    str(x) + ":" + str(boosting_tokens[x]) + "^" + str(boost_val)

            return query_string + boost_string

if __name__ == '__main__':
    lucene.initVM(vmargs=['-Djava.awt.headless=true'])
    
    query_gen = QueryGenerator(StandardAnalyzer())

    boosting_tokens = {
                        "title":"cabana",
                        "path":"root",    
                        "subject1":"subj"
                    }
    query_string = "what is my name "
    
    search_query = query_gen.build_query(query_string, boosting_tokens,"OR_QUERY")

    print(search_query)
