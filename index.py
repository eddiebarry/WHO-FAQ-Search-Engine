#!/usr/bin/env python

import sys, os, lucene, threading, time, json
from datetime import datetime

from java.nio.file import Paths
from org.apache.lucene.analysis.miscellaneous import LimitTokenCountAnalyzer
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.document import Document, Field, FieldType
from org.apache.lucene.index import \
    FieldInfo, IndexWriter, IndexWriterConfig, IndexOptions
from org.apache.lucene.store import SimpleFSDirectory

from variation_generation.variation_generator import VariationGenerator


class IndexFiles:
    """
    A pylucene based class for indexing json objects

    Queries generated by the QueryGenerator class present in 
    query_generator.py are used to query the search indexes built by this 
    class

    This class functions as a pythonic wrapper that exposes the functionality
    of the IndexWriter class in lucene

    Attributes
    ----------
    storeDir : String
        The directory where we want to store the generated index
        This directory can then be used by the SearchEngine class for serving
    store : SimpleFSDirectory
        A Lucene FS directory which points to the built search index being
        modified
    analyser : Any Lucene Analyzer
        A Lucene Analyzer for preprocessing text data
    config : IndexWriterConfig
        An object which contains information for how the config is being
        modified
    doc_and_freq_fieldtype : Lucene FieldType
        When text is writen to a lucene index, certain metadata about the
        text is stored along with the raw text data
        This attribute is used to specify what kind of metadata we want to 
        store
    writer : Lucene IndexWriter
        This object is used to write data to the index. 
        To use this object, First a lucene document must be created
        Then the lucene document must be staged for writing to the index
        After staging, the writer needs to be commited and closed.
    should_generate_variations : Boolean
        Wether the indexer should generate variations of a given field and 
        store them in the index
    variation_generator : VariationGenerator
        A python class which uses doct5query to create variations of a given
        sentence
    fields_to_expand : List[String]
        If query variations need to be generated, only a particular set of 
        fields will benefit from variation generation. The keys of these 
        fields must be specified for the fields that must be expanded


    Methods
    __init__(store_dir, analyzer)
        This method sets up the storage directory and initialises
        the attributes to the default values.
    
    get_doc_and_freq_fieldtypes()
        Initialises a fieldtype which stores the document as well as
        the document frequencies as metadata
    
    getIndexDir()
        Returns the directory where the current index is being stored
    
    indexFolder(indexDir)
        Takes all the files present in the indexDir and stores them in the
        index
    
    indexJsonPath(jsonpath)
        Reads the json file which jsonpath points to and adds all the 
        key value pairs present inside to the index
    
    indexJsonArray(jsonArray, list_name)
        Adds all the dictionary objects present in the list_name field
        of the jsonArray to the index
    """ 

    def __init__(self, storeDir, analyzer=None, \
        variation_generator_config = [False, None, [None]])
        """
        This method sets the directory in which the index is stored,
        adds the configuration for the lucene index as well as
        specifies what kind of metadata is stored in the index
        
        Inputs
        ------
        storeDir : String
            The directory in which the index will be stored
        analyser : Any Lucene Analyzer
            The lucene analyser which will be used by the different parts
            of the input pipeline
        variation_generation_config : Python list \
                [
                    should_expand_queries : Boolean, 
                    variation_generator : VariationGenerator, 
                    fields_to_expand : List[String]
                ]
            This config file is used to specify the info needed for
            variation generation which must contain :

                should_expand_queries
                    The value is a boolean flag which specifies that
                    variation generation must be used
                variation_generator
                    The variation generator class which managed the 
                    generation of alternative 
                fields_to_expand
                    A list of keys, which if present in the json will be
                    expanded

                    For example, in the json :
                    {
                        "id": "doc1",
                        "contents": "contents of doc one.",
                        "keywords": "Vaccine 1",
                        "Disease": "Disease 1",
                    }

                    if fields_to_expand == ["contents","Disease"]
                    Then variations of "contents" and "Disease" are generated
        """
        if not os.path.exists(storeDir):
            os.mkdir(storeDir)
        if not analyzer:
            analyzer = StandardAnalyzer()

        self.storeDir = storeDir
        self.store = SimpleFSDirectory(Paths.get(storeDir))
        self.analyzer = LimitTokenCountAnalyzer(analyzer, 1048576)
        self.config = IndexWriterConfig(analyzer)
        self.config.setOpenMode(IndexWriterConfig.OpenMode.CREATE)
        self.doc_and_freq_fieldtype = self.get_doc_and_freq_fieldtype()
        self.doc_fieldtype = self.get_doc_fieldtype()
        self.writer = None

        self.should_expand_queries, \
        self.query_expander \
        self.fields_to_expand = variation_generator_config
    
    def get_doc_and_freq_fieldtype(self):
        """
        When data is stored in an index, we can choose to store various
        metadata about the document. For example, we can store
        DOCS_AND_FREQS or DOCS_AND_FREQS_AND_POSITIONS such as line 69 in        
        https://svn.apache.org/viewvc/lucene/pylucene/trunk/samples/IndexFiles.py?view=markup

        Here we set the field type to only store document and frequency
        """
        t1 = FieldType()
        t1.setStored(True)
        t1.setTokenized(True)
        t1.setIndexOptions(IndexOptions.DOCS_AND_FREQS)
        return t1
    
    def get_doc_fieldtype(self):
        """
        When data is stored in an index, we can choose to store various
        metadata about the document. For example, we can store
        DOCS_AND_FREQS or DOCS_AND_FREQS_AND_POSITIONS such as line 69 in        
        https://svn.apache.org/viewvc/lucene/pylucene/trunk/samples/IndexFiles.py?view=markup

        Here we set the field type to only store document and frequency
        """
        t1 = FieldType()
        t1.setStored(True)
        t1.setTokenized(True)
        t1.setIndexOptions(IndexOptions.DOCS)
        return t1

    def getIndexDir(self):
        """ Returns the directory in which the index is stored"""
        return self.storeDir
    
    # TODO : Make changes when we want to expand queries
    def indexFolder(self, indexDir):
        """
        Adds all the json files present in indexDir to the index
        """
        print( 'Writing directory to index')
        self.writer = IndexWriter(self.store, self.config)
        # TODO : Check if indexDir is a real index
        for filename in sorted(os.listdir(indexDir)):
            if not filename.endswith('.json'):
                continue
            
            print("adding", filename)
            self.indexJsonPath(os.path.join(indexDir,filename))
            
        self.writer.commit()
        self.writer.close()
        print( 'done')
        
    # TODO : Make changes when we want to expand queries
    def indexJsonPath(self, jsonpath):
        """
        Adds the json file which jsonpath points to, to the index
        Adds all possible key Value pairs present
        """
        if os.path.isfile(jsonpath) and jsonpath.endswith(".json"):
            try:
                f = open(jsonpath,)
                jsonObj = json.load(f)

                doc = self.getDocumentToIndex(jsonObj)
                self.writer.addDocument(doc)

            except Exception as e:
                print( "Failed in indexDocs:", e)
    
    # TODO : Store the created Json Objects
    def indexJsonArray(self, jsonArray, list_name = "QA_Pairs"):
        """
        Takes all objects inside the json array and adds them to the
        index
        """
        print( 'writing json array to index')
        self.writer = IndexWriter(self.store, self.config)
        for jsonObj in jsonArray[list_name]:
            try:    
                doc = self.getDocumentToIndex(jsonObj)
                self.writer.addDocument(doc)

            except Exception as e:
                print( "Failed in indexDocs:", e)
        
        self.writer.commit()
        self.writer.close()
        print( 'done')

    # TODO : write a single json file to index and commit
    def getDocumentToIndex(self,jsonObj):
        """
        Given a loaded json Object, generates the corresponding lucene document
        which must be added in the index.
        This includes the generation of variations of fields that we must store
        """
        doc = Document()

        for x in jsonObj.keys():
            if x.replace(" ","_") in self.fields_to_expand:
                label = x.replace(" ","_")
                variations = self.variation_generator.get_variations(jsonObj[x])
                for idx, variation in enumerate(variations):
                    field_name = label + "_variation_"+str(idx)
                    doc.add(Field(field_name, variation, self.doc_fieldtype))        
            # TODO : Check if key values are strings
            doc.add(Field(x.replace(" ","_"), jsonObj[x], \
                self.doc_and_freq_fieldtype))

        return doc



if __name__ == '__main__':
    lucene.initVM(vmargs=['-Djava.awt.headless=true'])
    print( 'lucene', lucene.VERSION)

    IndexTest = IndexFiles("./IndexFiles.Index")
    IndexTest.indexFolder("./test_data")

    print(IndexTest.getIndexDir())

    # TODO: Write tests

    
    
