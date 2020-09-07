#!/usr/bin/env python

import sys, os, lucene

from java.nio.file import Paths
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.index import DirectoryReader
from org.apache.lucene.queryparser.classic import QueryParser
from org.apache.lucene.store import SimpleFSDirectory
from org.apache.lucene.search import IndexSearcher

from synonym_expansion.synonym_expander import SynonymExpander

class QueryGenerator:
    """
    A lucene query generator using PyLucene
    
    This class parses the user input, recieves tokens which need boosting
    and generates a lucene query which contains the boosts the given tokens

    Attributes
    ----------
    analyser : Any Lucene Analyzer
        A Lucene Analyzer for preprocessing text data

    Methods
    -------
    __init__(analyzer, use_synonyms)
        The init method takes an analyzer which is used while parsing a
        user query into a lucene query as well as sets wether synonyms
        must be used
    
    build_query(query_string, boosting_tokens, query_type, default_field)
        Takes a user query, takes a dictionary of boosting tokens and
        generates a lucene query where tokens are boosted

    get_or_query_string(query_string, boosting_tokens, boost_val)
        In lucene, OR queries are queries that may contain the search terms
        Having the exact search terms is not a strict necessity

        This method generates a OR query for the given boosting tokens
    """

    def __init__(self, analyzer, \
        use_synonyms=False, synonyms_boost_val=0.5):
        """ Take a standard analyzer for query generation """
        self.analyzer = analyzer
        self.use_synonyms = use_synonyms
        self.synonyms_boost_val = None

        if self.use_synonyms:
            self.synonym_expander = SynonymExpander()
            self.synonyms_boost_val = synonyms_boost_val
        
    
    # TODO : Remove Stop words
    def build_query(self, query_string, boosting_tokens, query_type, \
        field="contents", boost_val=1.05):
        """
        First, the user query is matched againt the field specifiec in 
        "field", then the boosting tokens are matched against the keys 
        of the dictionary with a uniform boosting value "boost_val"

        The format of the boosting tokens is
        boosting_tokens = {
            "keywords":["love"],    
            "subject1":["care"]
        }

        Inputs
        ------
        query_string : String
            The string input by the user
        boosting_tokens : Dictionary
            The dictionary of tokens which need to be boosted according
            to the format specified above. The key of the dictionary is
            the field while the value is the token
        query_type : String
            The query type is the string which specifies what type of
            lucene query we should use
        """

        # TODO : sanitize query string sp that false queries dont break
        # the system. Prevent sql njection type attacks
        if query_type == "OR_QUERY":
            # TODO : add ability to have a per field unique boost value
            query_string = \
                self.get_or_query_string(query_string, \
                boosting_tokens, boost_val=boost_val)

        field = field.replace(" ","_")
        query = QueryParser(field, self.analyzer).parse(query_string)
        return query

    def get_or_query_string(self, query_string, boosting_tokens, boost_val):
        """
        Converts the user query string and boosting tokens into a long 
        OR query
        
        The format of the boosting tokens is
        boosting_tokens = {
            "keywords":["love"],    
            "subject1":["care"]
        }

        Inputs
        ------
        query_string : String
            The string input by the user
        boosting_tokens : Dictionary
            The dictionary of tokens which need to be boosted according
            to the format specified above. The key of the dictionary is
            the field while the value is the token
        boost_val : Float
            The amount of boosting that must be added per boosting token
        """

        if boost_val:
            # TODO : Boost a token according to a per field value
            boost_string = ""
            for x in boosting_tokens:
                for token in boosting_tokens[x]:
                    boost_string = boost_string + " OR " + \
                    str(x).replace(" ","_") + ":" + str(token) + "^" + str(boost_val)

            #TODO : Check Better methods of generating queries
            if self.use_synonyms and self.synonym_expander:
                synonyms = self.synonym_expander.return_synonyms(query_string)
                if len(synonyms) > 0:
                    query_string = query_string + \
                        " OR (" + " ".join(synonyms) + ")^" + \
                        str(self.synonyms_boost_val)

            return (query_string + boost_string).replace('/','\/')
            

if __name__ == '__main__':
    lucene.initVM(vmargs=['-Djava.awt.headless=true'])
    
    query_gen = QueryGenerator(StandardAnalyzer())

    boosting_tokens = {
                        "title":["cabana","banana"],
                        "path":["root"],    
                        "subject1":["subj"]
                    }
    query_string = "what is my name "
    
    search_query = query_gen.build_query(query_string, boosting_tokens,"OR_QUERY")

    print(search_query)

    # Testing the synonyms
    query_gen = QueryGenerator(StandardAnalyzer(), use_synonyms=True)

    boosting_tokens = {
                        "title":["cabana","banana"],
                        "path":["root"],    
                        "subject1":["subj"]
                    }
    query_string = "what is my daughter's name "
    
    search_query = query_gen.build_query(query_string, boosting_tokens,"OR_QUERY")

    print(search_query)
