import torch
from transformers import T5Config, T5Tokenizer, T5ForConditionalGeneration



class QueryExpander:
    """
    Use this class for generating variations of a question.
    """

    # TODO : Think about model weights management + retraining
    def __init__(self, max_length=1024, num_variations=3,\
        path="./query_expander_model_weights/model.ckpt-1004000"):
        """
        Setup docT5 query generator for generating variations of a query

        Inputs
        ------
        max_length : Integer
            The default maximum length of the generated variation
        num_variations : Integer
            The default number of variations that must be generated.
            Can be overriden by the calling function
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        self.tokenizer = T5Tokenizer.from_pretrained('t5-base')
        config = T5Config.from_pretrained('t5-base')
        
        self.model = T5ForConditionalGeneration.from_pretrained(\
            path, from_tf=True, config=config)
        self.model.to(self.device)
        
        self.max_length = max_length
        self.num_variations = num_variations

    def get_variations(self, sent, num_variations=None):
        """
        Given a sentence, generate variations of it

        Inputs
        ------
        num_variations : Integer
            The number of variations we want to generate for a given sentence
        """
        input_ids = tokenizer.encode(sent, return_tensors='pt').to(device)
        
        if num_variations:
            outputs = model.generate(
                input_ids=input_ids,
                max_length=self.max_length,
                do_sample=True,
                top_k=10,
                num_return_sequences=num_variations)
        else:
            outputs = model.generate(
                input_ids=input_ids,
                max_length=self.max_length,
                do_sample=True,
                top_k=10,
                num_return_sequences=self.num_variations)

        generated_variations = [ tokenizer.decode(output, skip_special_tokens=True) \
            for output in outputs]
        
        return generated_variations

if __name__ == '__main__':
    qry_exp = QueryExpander()
    print(qry_exp.get_variations("Do vaccines cause autism ?"))

