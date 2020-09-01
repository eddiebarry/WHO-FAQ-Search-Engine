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
    # TODO : Add synonym expansion from syn_list.txt
    def __init__(self):
        """
        Setup Synonym Expander with spacy pipleline for synonym replacement
        """
        # Load an spacy model (supported models are "es" and "en") 
        nlp = spacy.load('en')
        nlp.add_pipe(WordnetAnnotator(nlp.lang), after='tagger')

        self.nlp = nlp
        self.domain_of_interest = ['person','economy']

    def expand_sentence(self, sent):
        """
        For a given sentence, replaces a word with the entire list of synonyms

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
        sentence = nlp(sent)

        # For each token in the sentence
        for token in sentence:
            # We get those synsets within the desired domains
            synsets = token._.wordnet.wordnet_synsets_for_domain(domain_of_interest)
            if not synsets:
                enriched_sentence.append(token.text)
            else:
                lemmas_for_synset = [lemma for s in synsets for lemma in s.lemma_names()]
                # If we found a synset in the economy domains
                # we get the variants and add them to the enriched sentence
                enriched_sentence.append('{}'.format(' '.join(set(lemmas_for_synset))))

        # Let's see our enriched sentence
        return ' '.join(enriched_sentence)