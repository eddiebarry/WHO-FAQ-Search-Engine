#!/usr/bin/env python

import sys, os, lucene

from java.nio.file import Paths
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.index import DirectoryReader
from org.apache.lucene.queryparser.classic import QueryParser
from org.apache.lucene.store import SimpleFSDirectory
from org.apache.lucene.search import IndexSearcher


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
    __init__(analyzer)
        The init method takes an analyzer which is used while parsing a
        user query into a lucene query
    
    build_query(query_string, boosting_tokens, query_type, default_field)
        Takes a user query, takes a dictionary of boosting tokens and
        generates a lucene query where tokens are boosted

    get_or_query_string(query_string, boosting_tokens, boost_val)
        In lucene, OR queries are queries that may contain the search terms
        Having the exact search terms is not a strict necessity

        This method generates a OR query for the given boosting tokens
    """

    def __init__(self, analyzer):
        """ Take a standard analyzer for query generation """
        self.analyzer = analyzer
    
    def build_query(self, query_string, boosting_tokens, query_type, \
        field="contents"):
        """
        First, the user query is matched againt the field specifiec in 
        "field", then the boosting tokens are matched against the keys 
        of the dictionary with a uniform boosting value "boost_val"

        The format of the boosting tokens is
        boosting_tokens = {
                    "fiels1":"love",    
                    "field2":"care"
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
                boosting_tokens, boost_val=1.05)

        query = QueryParser(field, self.analyzer).parse(query_string)
        return query

    def get_or_query_string(self, query_string, boosting_tokens, boost_val):
        """
        Converts the user query string and boosting tokens into a long 
        OR query
        
        The format of the boosting tokens is
        boosting_tokens = {
                    "fiels1":"love",    
                    "field2":"care"
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
                boost_string = boost_string + " OR " + \
                    str(x) + ":" + str(boosting_tokens[x]) + "^" + str(boost_val)

            #TODO : Check Better methods of generating queries
            return (query_string + boost_string).replace('/','\/')
<<<<<<< HEAD
=======

>>>>>>> 91976c40a5d0cba79ec2c9d2f56e8453f12cafe3

# TODO: Document
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
