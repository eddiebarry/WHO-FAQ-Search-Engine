#!/usr/bin/env python

import sys, os, lucene

from java.nio.file import Paths
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.index import DirectoryReader
from org.apache.lucene.queryparser.classic import QueryParser
from org.apache.lucene.store import SimpleFSDirectory
from org.apache.lucene.search import IndexSearcher


class SearchEngine:
    """ 
    A pylucene based search class
    
    This class serves a Lucene index built by the "IndexFiles" class
    present in Index.py
    
    To query the lucene index, a query needs to be built by the 
    QueryGenerator class

    This class supports the ability to "Hot Swap" indexes using the update
    function

    The search results are served via a json or JavaDocs format


    Attributes
    ----------
    diectory : SimpleFSDirectory
        A Lucene FS directory which points to a pre built search index
    searcher : IndexSearcher
        A Lucene Index Searcher
    analyser : Any Lucene Analyzer
        A Lucene Analyzer for preprocessing text data


    Methods
    -------
    __init__(index_dir)
        Sets up the lucene index searcher to read the index provided in
        "index_dir"
    
    update(new_dir):
        Sets up the lucene index searcher to read the index provided in
        "new_dir"
        
        Once we download a new index from an external source, the running
        searcher can be pointed towards a new index to hot swap the results
    
    search(query, top_n=50):
        The main function used for searching an index. Intentionally kept
        to the bare minimum for latency reasons

        Returns the top n results according to the scoring function
    """

    def __init__(self, index_dir):
        """
        The search class needs to be initialised with a directory which
        points to the lucene index which is being served

        Once it is pointed to the directory, This function initialises 
        an IndexSearcher for the given index

        Inputs
        ------
        index_dir : String
            A string which is the path to a lucene based index
        """

        # TODO: Check that the indexdir points to a valid lucene index
        self.directory = \
            SimpleFSDirectory(Paths.get(index_dir))
        self.searcher = \
            IndexSearcher(DirectoryReader.open(self.directory))
        
        # TODO: Explore different kinds of analyzers
        self.analyzer = StandardAnalyzer()
    
    def update(self, new_dir):
        """
        The search class needs to be initialised with a directory which
        points to the lucene index which is being served

        Once it is pointed to the directory, This function initialises 
        an IndexSearcher for the given index

        This function is enabled so that we can hot swap a newly created 
        index using

            SearchEngine.update(path_to_new_index)

        Inputs
        ------
        new_dir : String
            A string which is the path to a lucene based index
        """

        # TODO: Check that the indexdir points to a valid lucene index
        self.directory = \
            SimpleFSDirectory(Paths.get(new_dir))
        self.searcher = \
            IndexSearcher(DirectoryReader.open(directory))
        self.analyzer = StandardAnalyzer()
    
    def search(self, query, top_n=50, return_json=False):
        """
        This function takes a lucene query which can be created from
        the lucene query parser class and performs a search on the index
        It then returns the top n results according to the ranking score

        Inputs
        ------
        query : Lucene Query
            A query create by the QueryGenerator class present in 
            query_generator.py
        top_n : Int
            The number of top results we want our search to return
        return_json: Bool
            If true, the search results are jsonified and returned
            else the search results are return in the Lucene Document format
        """

        # TODO : Use BM25 with Anserini hyper params
        scoreDocs = self.searcher.search(query, top_n)
        if return_json:
            jsonDocs = self.convert_to_json(scoreDocs)
            return jsonDocs
        else:
            return scoreDocs
    
    def return_doc(self,doc_id):
        """ 
        A function for returning a document from the lucene index
<<<<<<< HEAD
        using it's unique internal identifier
=======
        using it's uniquer internal identifier
>>>>>>> 91976c40a5d0cba79ec2c9d2f56e8453f12cafe3
        """
        return self.searcher.doc(doc_id)

    # TODO: Specify the data format and implement the function
    def convert_to_json(self, scoreDocs):
        """
        A function for converting the internal search results
        form the javadoc format to a json object
        """
        pass


# TODO document
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