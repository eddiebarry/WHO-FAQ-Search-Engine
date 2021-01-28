import torch
from transformers import T5Config, T5Tokenizer, T5ForConditionalGeneration
torch.backends.cudnn.deterministic = True
torch.manual_seed(0)


class VariationGenerator:
    """
    Use this class for generating variations of a question.
    """

    # TODO : Think about model weights management + retraining
    def __init__(self, max_length=20, num_variations=3,\
        path="./variation_generator_model_weights/model.ckpt-1004000"):
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

        # self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # self.tokenizer = T5Tokenizer.from_pretrained("/usr/src/WHOA-FAQ-Answer-Project/WHO-FAQ-Search-Engine/variation_generation/models/")
        # config = T5Config.from_json_file('/usr/src/WHOA-FAQ-Answer-Project/WHO-FAQ-Search-Engine/variation_generation/T5config.json')
        
        # # TODO : Add model weight download
        # # self.model = torch.load(path, map_location=self.device)
        # self.model = T5ForConditionalGeneration.from_pretrained(\
        #     path, from_tf=True, config=config)
        # self.model.to(self.device)
        # self.model.eval()
        
        self.path = path
        self.max_length = max_length
        self.num_variations = num_variations
        self.initialised = False

    def custom_init(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        self.tokenizer = T5Tokenizer.from_pretrained("/usr/src/WHOA-FAQ-Answer-Project/WHO-FAQ-Search-Engine/variation_generation/models/")
        config = T5Config.from_json_file('/usr/src/WHOA-FAQ-Answer-Project/WHO-FAQ-Search-Engine/variation_generation/T5config.json')
        
        # TODO : Add model weight download
        # self.model = torch.load(path, map_location=self.device)
        self.model = T5ForConditionalGeneration.from_pretrained(\
            self.path, from_tf=True, config=config)
        self.model.to(self.device)
        self.model.eval()
        
        self.max_length = max_length
        self.num_variations = num_variations
        self.initialised = True


    def get_variations(self, sent, num_variations=None):
        """
        Given a sentence, generate variations of it

        Inputs
        ------
        num_variations : Integer
            The number of variations we want to generate for a given sentence
        """
        if not self.initialised:
            self.custom_init()

        input_ids = self.tokenizer.encode(sent, return_tensors='pt')\
            .to(self.device)
        
        if num_variations:
            outputs = self.model.generate(
                input_ids=input_ids,
                max_length=self.max_length,
                do_sample=True,
                top_k=1000,
                num_return_sequences=num_variations)
        else:
            outputs = self.model.generate(
                input_ids=input_ids,
                max_length=self.max_length,
                do_sample=True,
                top_k=10,
                num_return_sequences=self.num_variations)

        generated_variations = [ self.tokenizer.decode(output, \
        skip_special_tokens=True) for output in outputs]
        
        return generated_variations

if __name__ == '__main__':
    variation_gen = VariationGenerator()
    doc_text = "In some areas of BC, parents are asked to submit \
        their children\'s immunization records to the school.  \
        After the immunization record has been given to your \
        school it is reviewed by your school's Public Health Nurse and \
        the information is entered into your child's health record at \
        your public health unit. All of the information is confidential. \
        This ensures the right vaccines are recommended for your child \
        in the future. School Medical Health Officers also need \
        these records for decisions should someone have a vaccine \
        preventable disease at your school. For more information, \
        please contact your local public health unit. "
    
    assert(\
        variation_gen.get_variations(doc_text)\
        ==\
        ['why do we need immunization records for school', \
         'why do school nurses get records for immunizations from children',\
         'why is immunization record needed for child'])
    # tokenizer = T5Tokenizer.from_pretrained('t5-base', cache_dir="new_cache_dir/")
    # config = T5Config.from_pretrained('t5-base', cache_dir="new_cache_dir/")

    # tokenizer.save_pretrained("./models/")
    # config.to_json_file("./config.json")

    # token = T5Tokenizer.from_pretrained("./models/")
    # config = T5Config.from_json_file("./config.json")

