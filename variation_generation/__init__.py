
from transformers import T5Config, T5Tokenizer, T5ForConditionalGeneration
tokenizer = T5Tokenizer.from_pretrained('t5-base', cache_dir="new_cache_dir/")
config = T5Config.from_pretrained('t5-base', cache_dir="new_cache_dir/")