import sys, os, json, requests, hashlib
import pysolr
import pdb

from rerank.ApiReranker import ApiReranker
from rerank.rerank_config import RE_RANK_ENDPOINT
from variation_generation.variation_generator import VariationGenerator
from synonym_expansion.synonym_expander import SynonymExpander

# Importing constants
from dotenv import load_dotenv
load_dotenv()


class SolrSearchEngine:
    """ 
    A solr based search class
    
    
    To query the index, a query needs to be built by the 
    QueryGenerator class

    The search results are served via a json or JavaDocs format


    Attributes
    ----------
    solr_server_link : String
        Url pointing to a solr server

    rerank_endpoint : String
        Url point to ML reranking server


    Methods
    -------
    __init__(solr_url, rerank_endpoint):
        Sets up the solr url endpoint as well as the ranking endpoint
    
    index(project_id, version_id, question_list):
        Takes the question list, generates variations and adds them to the index

    get_json_to_add(question_pair):

    
    search(query, top_n=50):
        The main function used for searching an index. Intentionally kept
        to the bare minimum for latency reasons

        Returns the top n results according to the scoring function
    """

    def __init__(self,\
        solr_url=os.getenv("SOLR_ENDPOINT"),\
        rerank_endpoint=None,\
        debug=False,\
        use_markdown=False,\
        use_rm3=False,\
        variation_generator_config=[False, None, [None]],\
        synonyms_boost_val=0.5,\
        synonym_config=[
            True, #use_wordnet
            True, #use_syblist
            "./synonym_expansion/syn_test.txt" #synlist path
        ]):
        """
        The search class needs to be initialised with a directory which
        points to the lucene index which is being served

        Once it is pointed to the directory, This function initialises 
        an IndexSearcher for the given index

        Inputs
        ------
        index_dir : String
            A string which is the path to a lucene based index
        rerank : Bool
            A Flag for wether a simple ML reranker must be used as part
            of the pipeline
        """
        self.solr_server_link = solr_url
        self.rerank_endpoint = rerank_endpoint
        
        self.variation_generator, \
        self.fields_to_expand = variation_generator_config
        
        self.synonyms_boost_val = None
        self.synonym_config = synonym_config

        if self.rerank_endpoint:
            self.reranker = ApiReranker(endpoint=self.rerank_endpoint)
            print("Using API Reranker")

        if synonym_config:
            use_wordnet, use_synlist, synlist_path = synonym_config
            self.synonym_expander = SynonymExpander(\
                use_wordnet=use_wordnet,
                use_synlist=use_synlist,
                synlist_path=synlist_path)
            self.synonyms_boost_val = synonyms_boost_val
        
        self.debug = debug
        self.use_markdown = use_markdown
        self.use_rm3 = use_rm3

    def index_prev_versions(self, project_id, version_id, previous_versions):
        # iterate over previous collections and add
        link = self.solr_server_link + "/solr/admin/collections"
        print(link, "is the prev link")
        x = requests.get(link,{"action":"LIST","wt":"json"})
    
        prev_versions = [str(x) for x in previous_versions]

        docs_to_add = []
        print(x.json()['collections'], "is the prev collections")
        for collection in x.json()['collections']:
            if 'qa' in collection:
                project_id_new, version_id_new = collection.split('_')[1:]

                if str(project_id_new) == str(project_id) and str(version_id_new) in prev_versions:
                    # copy all documents
                    index_url = self.solr_server_link + "/solr/" + collection
                    solr = pysolr.Solr(index_url)

                    results = solr.search("*:*",rows=200000000)
                    docs = [x for x in results]
                    
                    docs_to_add.extend(docs)

        for x in docs_to_add:
            x.pop('_version_')
            for key in x:
                x[key]=x[key][0]

        print("Adding ", len(docs_to_add), "documents from old versions to new index")
        self.index(project_id,version_id,docs_to_add)

    
    def index(self, project_id, version_id, question_list):
        """
        This function adds QA pairs to the search index after generating 
        variations

        Inputs
        ------
        project_id : String
            A string which states to the project being used
        
        version_id : String
            A string which states to the version being used
        """
        proj_exists = self.ensure_collection_exists(project_id,version_id)
        if proj_exists:
            index_url = self.solr_server_link + "/solr/" + proj_exists
            client = pysolr.Solr(index_url, always_commit=True)

            to_add = []
            for question in question_list:
                if 'id' not in question.keys():
                    question['id']=hashlib.sha512(question['question'].encode())\
                        .hexdigest()

                if self.use_rm3:
                    question['para_text_bm']=question['question']
                    question['para_text_ql']=question['question']
                
                question_with_variation = self.preprocess_question(question)
                to_add.append(question_with_variation)
            
            print("sending to solr server", proj_exists)
            client.add(to_add)
            print("recieved by solr server", proj_exists)

    def preprocess_question(self, question):
        processed_question = {}
        for x in question.keys():
            if question[x]=="" or question[x] =="-":
                continue
            if "variation" in x:
                continue

            if x.replace(" ","_") in self.fields_to_expand:
                label = x.replace(" ","_")
                cached = True
                field_names = []

                if self.variation_generator:
                    for idx in range(self.variation_generator.num_variations):
                        field_name = label + "_variation_"+str(idx)
                        field_names.append(field_name)
                        cached = cached and field_name in question.keys()

                    if cached:
                        variations = [question[key] for key in field_names]
                    else:
                        variations = self.variation_generator.\
                            get_variations(question[x])

                    for idx, variation in enumerate(variations):
                        field_name = label + "_variation_"+str(idx)
                        processed_question[field_name] = variation
            processed_question[x]=question[x]

        return processed_question

    def ensure_collection_exists(self, project_id, version_id):
        collection_url = self.solr_server_link + "/solr/admin/collections"
        # Check collection names
        collection_json = requests.get(\
            collection_url,{"action":"LIST","wt":"json"})#.json()
        
        collection_json = collection_json.json()
        
        if collection_json['responseHeader']['status'] != 0:
            return False

        all_collections = collection_json['collections']

        new_name = "qa_"+str(project_id)+"_"+str(version_id)
        if new_name not in all_collections:
            # Create a collection if collection doesnt exist
            if self.use_rm3:
                #First create a custom configset
                headers = {
                    'Content-Type': 'application/octet-stream',
                }
                configName = new_name
                params = (
                    ('action', 'UPLOAD'),
                    ('name', configName),
                )
                
                data = open('/usr/src/WHOA-FAQ-Answer-Project/WHO-FAQ-Search-Engine/configs/myconfigset.zip', 'rb').read()
                response = requests.post(self.solr_server_link \
                    +'/solr/admin/configs', 
                    headers=headers, 
                    params=params, 
                    data=data)
                # pdb.set_trace()

                x = requests.get(collection_url,\
                {
                    "action":"CREATE","name":new_name,"numShards":"1",
                    "collection.configName":configName, "replication_factor":"2"
                })
            else:
                x = requests.get(collection_url,\
                    {"action":"CREATE","name":new_name,"numShards":"1", "replication_factor":"2"})
        return new_name
    
    def indexFolder(self, indexDir,project_id=10, version_id=20):
        """
        Adds all the json files present in indexDir to the index
        """
        print( 'Writing directory to index')
        question_list = []
        for filename in sorted(os.listdir(indexDir)):
            if not filename.endswith('.json'):
                continue            
            # print("adding", filename)
            
            f = open(os.path.join(indexDir,filename),)
            question = json.load(f)
            question_list.append(question)

        # pdb.set_trace()
        self.index(project_id,version_id,question_list)

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
        query_string = query_string.replace("?","").replace("(","")\
                .replace(")","").replace("-","").replace("\"","").replace("'","").strip()

        if query_type == "OR_QUERY":
            synonyms = None

            # Ask against field
            new_field = field+":"
            qs = ""
            for x in query_string.split(" "):
                qs+= new_field + "\""+ x + "\" "

            query_string = qs
            # TODO : add ability to have a per field unique boost value
            if self.debug:
                query_string, synonyms = \
                    self.get_or_query_string(query_string,
                    boosting_tokens, boost_val=boost_val, field=field)
            else:
                query_string, _ = \
                    self.get_or_query_string(query_string,
                    boosting_tokens, boost_val=boost_val, field=field)

        if query_type == "RM3_QUERY":
            query_string, synonyms = self.get_rm3_query_string(
                query_string,
                boosting_tokens)

        if self.debug:
            return query_string, synonyms
        return query_string

    def get_rm3_query_string(self, query_string, boosting_tokens):
        """
        Converts the user query string and boosting tokens into a long 
        RM3 query
        
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
        """
        boost_string = ""
        # if boost_val:
        for x in boosting_tokens:
            for token in boosting_tokens[x]:
                if token == "":
                    continue
                boost_string = boost_string + " " + str(token)

        return (query_string + boost_string).replace('/','\/'), False

    def get_or_query_string(self, query_string, boosting_tokens, boost_val, field):
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

        boost_string = ""
        if boost_val:
            # TODO : Boost a token according to a per field value
            for x in boosting_tokens:
                for token in boosting_tokens[x]:
                    if token == "":
                        continue
                    boost_string = boost_string + " OR " + \
                    str(x).replace(" ","_") + ":\"" + str(token) + "\"^" + \
                        str(boost_val)

        #TODO : Check Better methods of generating queries
        if self.synonym_config:
            synonyms = self.synonym_expander.return_synonyms(query_string)
            if len(synonyms) > 0:
                qs = ""
                new_field = field+":"
                for x in synonyms:
                    qs+= new_field + x + " "

                query_string = query_string + \
                    " OR (" + qs + ")^" + \
                    str(self.synonyms_boost_val)

        return (query_string + boost_string).replace('/','\/'), synonyms

    def search(self, query, project_id, version_id, top_n=50, return_json=False, \
        query_string=None, query_field=None):
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
        return_json : Bool
            If true, the search results are jsonified and returned
            else the search results are return in the Lucene Document format
        query_string : String
            The string entered by the user
        rerank_fiels : String
            The name of the field against which the reranker must be run
        """
        # Field names do not contain spaces
        query_field = query_field.replace(" ","_")

        proj_exists = self.ensure_collection_exists(project_id,version_id)
        if proj_exists:
            index_url = self.solr_server_link + "/solr/" + proj_exists

        if not proj_exists:
            return 400

        if self.use_rm3 and index_url:
            new_url = index_url + '/anserini'
            response = requests.get(new_url,{"q":query})
            data = response.json()
            # pdb.set_trace()
            docs = data['docs']['docs']
            
            for idx, x in enumerate(docs):
                for key in x:
                    x[key] = [x[key]]
                x['id']=str(idx)
            search_results_list = [x for x in docs]
            """
            the resonse contains these keys
            dict_keys(
                [
                    'question', 
                    'answer',
                    'answer_formatted', 
                    'question_variation_0', 
                    'question_variation_1', 
                    'question_variation_2', 
                    'score', 
                    'id'
                ]
            )
            """          
            # pdb.set_trace()
        else:
            client = pysolr.Solr(index_url, always_commit=True)
            search_results = client.search(query,rows=top_n)
            
            # pdb.set_trace()
            search_results_list = [x for x in search_results]

            max_score = search_results.raw_response['response']['maxScore']
            # pdb.set_trace() 
            if max_score < 7.5:
                return "Not present"
            #TODO: get scores as well 
            """
            the resonse contains these keys
            dict_keys(
                [
                    'answer', 
                    'answer_formatted', 
                    'disease_1', 
                    'disease_2', 
                    'question_variation_0', 
                    'question_variation_1', 
                    'question_variation_2', 
                    'question', 
                    'subject_1_immunization', 
                    'vaccine_1', 
                    'who_is_writing_this', 
                    'id', 
                    '_version_'
                ]
            )
            """
            
        
        # TODO : Add support for reranking multiple fields
        if self.rerank_endpoint is not None and query_string and query_field:
            ids = {}
            text = []

            for document in search_results_list:
                ids[document['question'][0]]=document['id']
                text.append([document['id'],document['question'][0]])

            scoreDocs = self.reranker.rerank(query_string, text)

            return_docs = []
            for x in scoreDocs:
                for y in search_results_list:
                    if x[1]==y['question'][0]:
                        return_docs.append([y,x[0]])
                        break
            # pdb.set_trace() 
        else:
            #TODO:setup so that score is correct
            # return document as well as score
            return_docs = []

        
        if self.debug:
            if query_field.endswith("*"):
                # mapper from text to doc
                fields = [
                        "question_variation_1",
                        "question_variation_0",
                        "answer",
                        "answer_formatted"
                    ]
            else:
                # only show qa
                fields = [
                        "answer",
                        "answer_formatted"
                    ]
            scoreDocs = []
            for doc in return_docs:
                text = doc[0][query_field.replace('*',"")][0]
                for field in fields:
                    text += " ||| " + doc[0][field][0]
                scoreDocs.append([doc[1],text])

        return scoreDocs

# TODO : Write Tests
if __name__ == '__main__':
    SearchEngineTest = SolrSearchEngine(
            rerank_endpoint=RE_RANK_ENDPOINT+"/api/v1/reranking",
            variation_generator_config=[
                VariationGenerator(\
                path="./variation_generation/variation_generator_model_weights/model.ckpt-1004000",
                max_length=5),   #variation_generator
                # None,
                ["question"] #fields_to_expand
            ],
            synonym_config=[
                True, #use_wordnet
                True, #use_syblist
                "./synonym_expansion/syn_test.txt" #synlist path
            ],
            debug=True,
        )

    SearchEngineTest.indexFolder(
        "../accuracy_tests/intermediate_results/vsn_data_formatted")

    boosting_tokens = {
                        "subject_1_immunization": ["Generic"],
                        "subject_2_vaccination_general": ["Booster"],
                        "subject_person": ["Unknown"],
                    }

    query_string = "I work in an independent living site, am I required to have a flu shot?"
    
    search_query, _ = SearchEngineTest.build_query(\
            query_string, \
            boosting_tokens,\
            "OR_QUERY",
            field="question"
        )

    print("search query is ", search_query)

    results = SearchEngineTest.search(
        query=search_query, 
        project_id="10", 
        version_id="20",
        query_field="question*",
        query_string=query_string)


    # RM3 Test
    SearchEngineTest = SolrSearchEngine(
            rerank_endpoint=RE_RANK_ENDPOINT+"/api/v1/reranking",
            variation_generator_config=[
                VariationGenerator(\
                path="./variation_generation/variation_generator_model_weights/model.ckpt-1004000",
                max_length=5),   #variation_generator
                # None,
                ["question"] #fields_to_expand
            ],
            synonym_config=[
                False,
                False,
                # True, #use_wordnet
                # True, #use_syblist
                "./synonym_expansion/syn_test.txt" #synlist path
            ],
            debug=True,
            use_rm3=True
        )

    SearchEngineTest.indexFolder(
        "../accuracy_tests/intermediate_results/vsn_data_formatted",
        version_id=30)

    boosting_tokens = {
                        "subject_1_immunization": ["Generic"],
                        "subject_2_vaccination_general": ["Booster"],
                        "subject_person": ["Unknown"],
                    }

    query_string = "I work in an independent living site, am I required to have a flu shot?"
    
    search_query, _ = SearchEngineTest.build_query(\
            query_string, \
            boosting_tokens,\
            "RM3_QUERY",
            field="question"
        )

    print("search query is ", search_query)

    results = SearchEngineTest.search(
        query=search_query, 
        project_id="10", 
        version_id="30",
        query_field="question*",
        query_string=query_string)