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

class IndexFiles:

    def __init__(self, storeDir, analyzer):
        if not os.path.exists(storeDir):
            os.mkdir(storeDir)

        self.storeDir = storeDir
        self.store = SimpleFSDirectory(Paths.get(storeDir))
        self.analyzer = LimitTokenCountAnalyzer(analyzer, 1048576)
        self.config = IndexWriterConfig(analyzer)
        self.config.setOpenMode(IndexWriterConfig.OpenMode.CREATE)
        self.doc_and_freq_fieldtype = self.get_doc_and_freq_fieldtype()
        self.writer = None
    
    def get_doc_and_freq_fieldtype(self):
        t1 = FieldType()
        t1.setStored(True)
        t1.setTokenized(True)
        t1.setIndexOptions(IndexOptions.DOCS_AND_FREQS)
        return t1
    
    def getIndexDir(self):
        return self.storeDir
    
    def indexFolder(self, indexDir):
        print( 'commit index')
        self.writer = IndexWriter(self.store, self.config)
        for filename in sorted(os.listdir(indexDir)):
            if not filename.endswith('.json'):
                continue
            
            print("adding", filename)
            self.indexJsonPath(os.path.join(indexDir,filename))
            
        self.writer.commit()
        self.writer.close()
        print( 'done')
        

    def indexJsonPath(self, jsonpath):
        if os.path.isfile(jsonpath):
            try:
                f = open(jsonpath,)
                jsonObj = json.load(f)

                doc = Document()

                for x in jsonObj.keys():
                    doc.add(Field(x, jsonObj[x], self.doc_and_freq_fieldtype))

                self.writer.addDocument(doc)

            except Exception as e:
                print( "Failed in indexDocs:", e)

if __name__ == '__main__':
    lucene.initVM(vmargs=['-Djava.awt.headless=true'])
    print( 'lucene', lucene.VERSION)

    IndexTest = IndexFiles("./IndexFiles.Index",StandardAnalyzer())
    IndexTest.indexFolder("./test_data")