import spacy

from spacy_wordnet.wordnet_annotator import WordnetAnnotator 

class SynonymExpander:
    """
    Use wordnet synonyms to expnd a user query for the search engine
    Converts : 
        My mom is sick with the fever. 
        
        She was bit by a dog. 
        
        Should i vaccinate with measles ?
    To :
        My (mamma|mom|mummy|mama|ma|momma|mum|mammy|mommy) 
        (constitute|cost|represent|make_up|comprise|be) sick with the fever. 
        
        She (constitute|cost|represent|make_up|comprise|be) bit by a 
        (cad|frump|bounder|dog|heel|blackguard|hound). 
        
        Should i vaccinate with measles ?
    """
    
    def __init__(self, use_wordnet=True,  \
            use_synlist=False, synlist_path="./synlist"):
        """
        Setup Synonym Expander with spacy pipleline for synonym replacement

        Inputs
        ------
        use_wordnet : Boolean
            Wether to query the wordnet DB for synonyms
        
        use_synlist : Boolean
            Wether to use manually specified synomnym lists
        
        synlist_path : String
            If use_synlist is set to True, a path to the synonymlist file
            must be specified
            The format of the synlist is

            A, B, C 
            ED, BG, CG

            Where each row is a set of synonyms
        """
        # Load an spacy model (supported models are "es" and "en") 
        nlp = spacy.load('en')
        nlp.add_pipe(WordnetAnnotator(nlp.lang), after='tagger')

        self.nlp = nlp
        self.domain_of_interest = ['person']

        self.all_stopwords = nlp.Defaults.stop_words

        self.use_wordnet = use_wordnet
        self.use_synlist = use_synlist

        if self.use_synlist:
            # TODO : Throw an error if path is not valid
            self.word_to_name_dict, self.name_to_syn_dict = \
                self.parse_synlist(synlist_path)


    def expand_sentence(self, sent, debug = False):
        """
        For a given sentence, replaces a word with the entire list of synonyms

        First get synonyms, create a list
        then create a boosted query

        Inputs
        ------
        sent : String
            The sentence which needs to be expanded into a string

            For eg : My child is big.
                will be replaced by :-

                My baby child toddler is big large
        """
        # Add a synonym list
        enriched_sentence = []
        sentence = self.nlp(sent)
        # Remove stopwords
        sentence= [word for word in sentence if not word in self.all_stopwords]

        # For each token in the sentence
        for token in sentence:
            # We get those synsets within the desired domains
            synsets = token._.wordnet.\
                wordnet_synsets_for_domain(self.domain_of_interest)
            if not synsets:
                enriched_sentence.append(token.text)
            else:
                lemmas_for_synset = [lemma for s in synsets \
                    for lemma in s.lemma_names()]
                # If we found a synset in the economy domains
                # we get the variants and add them to the enriched sentence
                if debug:
                    enriched_sentence.append(\
                        '({})'.format(
                            ('|'.join(set(lemmas_for_synset)))).replace('_',' ')\
                        )
                else:
                    enriched_sentence.append(\
                        '{}'.format(\
                            (' '.join(set(lemmas_for_synset)))).replace('_', ' ')\
                        )

        # Let's see our enriched sentence
        return ' '.join(enriched_sentence)
    
    def return_synonyms(self, sent):
        """
        For a given sentence, returns all synonyms present in it

        For eg : My child is big.
            will give

            ["baby", "child", "toddler", "big" , "large"]

        Inputs
        ------

        sent : String
            The sentence which needs to be expanded into a string
        """
        synonyms = []
        if self.use_wordnet:
            # Add a synonym list
            sentence = self.nlp(sent)
            # Remove stopwords
            sentence= [word for word in sentence if not word in self.all_stopwords]

            # For each token in the sentence
            for token in sentence:
                # We get those synsets within the desired domains
                synsets = token._.wordnet.\
                    wordnet_synsets_for_domain(self.domain_of_interest)
                if not synsets:
                    continue
                else:
                    lemmas_for_synset = [lemma for s in synsets \
                        for lemma in s.lemma_names()]
                    
                    if len(set(lemmas_for_synset)) <= 1:
                        continue
                    # If we found a synset in the economy domains
                    # we get the variants and add them to the enriched sentence
                    for x in set(lemmas_for_synset):
                        synonyms.append( "\"{}\"".format(x.replace('_',' ')))
            
        if self.use_synlist:
            sentence = self.nlp(sent)
            for word in sentence:
                if word.text in self.word_to_name_dict.keys():
                    key = self.word_to_name_dict[word.text]
                    synonyms.extend(self.name_to_syn_dict[key])
            
        return synonyms

    def parse_synlist(self, path):
        """
        parse a file to create 2 dictionaries

        word -> synonym group name
        synonym group name -> all synonym group words
        """

        word_to_name_dict = {}
        name_to_syn_dict  = {}

        with open(path) as f:
            for line in f:
                synonyms = [word.strip() for word in line.split(',')]
                syn_name  = synonyms[0]
                for word in synonyms:
                    word_to_name_dict[word] = syn_name
                
                syn_dict = set(synonyms)
                name_to_syn_dict[syn_name] = syn_dict

        return word_to_name_dict, name_to_syn_dict


if __name__ == '__main__':
    syn_exp = SynonymExpander()
    
    sent = "My daughter is 10 years old. What is a good vaccine ?"
    print(syn_exp.expand_sentence(sent, debug=True))

    print( "This is the model input")
    print(syn_exp.expand_sentence(sent, debug=False))

    print("Now we shall show the synonyms")
    print('='*80)
    print(syn_exp.return_synonyms(sent))

    print( "This is the model input")
    print(syn_exp.return_synonyms(sent))

    # Try using a synlist
    synlist_path="./syn_test.txt"
    f = open(synlist_path, "w")
    f.write("apple, granny smith, washington red\nboy, child, son, daughter\n")
    f.close()
    syn_exp_syn_list = SynonymExpander(\
        use_synlist=True, use_wordnet=False, synlist_path=synlist_path)
    
    print(syn_exp_syn_list.return_synonyms("My boy likes apple."))
    

