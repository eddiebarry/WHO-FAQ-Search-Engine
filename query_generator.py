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
    __init__(analyzer, synonym_config, synonym_boost_val)
        The init method takes an analyzer which is used while parsing a
        user query into a lucene query as well as sets wether synonyms
        must be used. If synonym expansion is used, their boost value
        is also taken
    
    build_query(query_string, boosting_tokens, query_type, default_field)
        Takes a user query, takes a dictionary of boosting tokens and
        generates a lucene query where tokens are boosted

    get_or_query_string(query_string, boosting_tokens, boost_val)
        In lucene, OR queries are queries that may contain the search terms
        Having the exact search terms is not a strict necessity

        This method generates a OR query for the given boosting tokens
    """

    def __init__(self, analyzer, synonyms_boost_val=0.5,\
        synonym_config=None, debug=False):
        """ 
        Take a standard analyzer for query generation 
        
        Inputs
        ------
        analyzer : Lucene Analyzer
            A lucene analyzer to use for parsing query
        synonym_boost_val : Float
            The value that generated synonyms must be boosted by
        synonym_config : Python List
            [
                use_wordnet : Boolean, 
                use_synlist : Boolean,
                synlist_path : String
            ]
            This config file is use to setup what kind of synonym expansion
            to use
                use_wordnet
                    This booelean is used to indicate wether wordnet expansion
                    must be used or not
                use_synlist
                    This boolean is used to indicate wether a custom specified
                    synlist should be used or not
                synlist_path 
                    This string is the path to the synlist to be used if 
                    use_synlist is set to true
        """
        self.analyzer = analyzer
        self.synonyms_boost_val = None
        self.synonym_config = synonym_config
        self.debug = debug

        if synonym_config:
            use_wordnet, use_synlist, synlist_path = synonym_config
            self.synonym_expander = SynonymExpander(\
                use_wordnet=use_wordnet,
                use_synlist=use_synlist,
                synlist_path=synlist_path)
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
        synonyms = None
        if query_type == "OR_QUERY":
            # TODO : add ability to have a per field unique boost value
            if self.debug:
                query_string, synonyms = \
                    self.get_or_query_string(query_string, \
                    boosting_tokens, boost_val=boost_val)
            else:
                query_string = \
                    self.get_or_query_string(query_string, \
                    boosting_tokens, boost_val=boost_val)

        field = field.replace(" ","_")
        query = QueryParser(field, self.analyzer).parse(query_string)

        if self.debug:
            return query, synonyms
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
                    if token == "":
                        continue
                    boost_string = boost_string + " OR " + \
                    str(x).replace(" ","_") + ":" + str(token) + "^" + \
                        str(boost_val)

            #TODO : Check Better methods of generating queries
            if self.synonym_config:
                synonyms = self.synonym_expander.return_synonyms(query_string)
                if len(synonyms) > 0:
                    query_string = query_string + \
                        " OR (" + " ".join(synonyms) + ")^" + \
                        str(self.synonyms_boost_val)
            
                if self.debug:
                    return (query_string + boost_string).replace('/','\/'), synonyms

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
    query_gen = QueryGenerator(StandardAnalyzer(), \
        synonym_config=[
            True, #use_wordnet
            True, #use_syblist
            "./synonym_expansion/syn_test.txt" #synlist path
        ])

    boosting_tokens = {
                        "title":["cabana","banana"],
                        "path":["root"],    
                        "subject1":["subj"]
                    }
    query_string = "what is my daughter's name "
    
    search_query = query_gen.build_query(query_string, boosting_tokens,"OR_QUERY")

    print(search_query)
