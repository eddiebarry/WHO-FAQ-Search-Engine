from copy import deepcopy
from typing import List, Mapping, Tuple, Union, Iterable, Optional, Any
from dataclasses import dataclass
import abc

import torch

from transformers import AutoTokenizer, T5ForConditionalGeneration
from transformers import PreTrainedTokenizer
from transformers import PreTrainedModel


TokenizerReturnType = Mapping[str, Union[torch.Tensor, List[int],
                                         List[List[int]],
                                         List[List[str]]]]
DecodedOutput = Union[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]

# TODO: Clean up code
class Query:
    """Class representing a query.
    A query contains the query text itself and potentially other metadata.
    Parameters
    ----------
    text : str
        The query text.
    id : Optional[str]
        The query id.
    """
    def __init__(self, text: str, id: Optional[str] = None):
        self.text = text
        self.id = id


class Text:
    """Class representing a text to be reranked.
    A text is unspecified with respect to it length; in principle, it
    could be a full-length document, a paragraph-sized passage, or
    even a short phrase.
    Parameters
    ----------
    text : str
        The text to be reranked.
    metadata : Mapping[str, Any]
        Additional metadata and other annotations.
    score : Optional[float]
        The score of the text. For example, the score might be the BM25 score
        from an initial retrieval stage.
    """

    def __init__(self,
                 text: str,
                 score: Optional[float] = 0):
        self.text = text
        self.score = score


class QueryDocumentBatch:
    def __init__(self, query: Query, documents: List[Text], \
                 output: Optional[TokenizerReturnType] = None):
        self.query = query
        self.documents = documents
        self.output = output

    def __len__(self):
        return len(self.documents)

class TokenizerEncodeMixin:
    def __init__(self, tokenizer: PreTrainedTokenizer = None, \
                 tokenizer_kwargs = None):
        self.tokenizer = tokenizer
        self.tokenizer_kwargs = tokenizer_kwargs

    def encode(self, strings: List[str]) -> TokenizerReturnType:
        assert self.tokenizer and self.tokenizer_kwargs is not None, \
                'mixin used improperly'
        ret = self.tokenizer.batch_encode_plus(strings,
                                               **self.tokenizer_kwargs)
        ret['tokens'] = list(map(self.tokenizer.tokenize, strings))
        return ret

class AppendEosTokenizerMixin:
    tokenizer: PreTrainedTokenizer = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def encode(self, strings: List[str]) -> TokenizerReturnType:
        assert self.tokenizer, 'mixin used improperly'
        return super().encode(
            [f'{x} {self.tokenizer.eos_token}' for x in strings])


class QueryDocumentBatchTokenizer(TokenizerEncodeMixin):
    def __init__(self,
                 tokenizer: PreTrainedTokenizer,
                 batch_size: int,
                 pattern: str = '{query} {document}',
                 **tokenizer_kwargs):
        self.tokenizer = tokenizer
        self.batch_size = batch_size
        self.tokenizer_kwargs = tokenizer_kwargs
        self.pattern = pattern

    def traverse_query_document(
            self,
            batch_input: QueryDocumentBatch) -> Iterable[QueryDocumentBatch]:
        query = batch_input.query
        for batch_idx in range(0, len(batch_input), self.batch_size):
            docs = batch_input.documents[batch_idx:batch_idx + self.batch_size]
            outputs = self.encode([self.pattern.format(
                                        query=query.text,
                                        document=doc.text) for doc in docs])
            yield QueryDocumentBatch(query, docs, outputs)

class T5BatchTokenizer(AppendEosTokenizerMixin, QueryDocumentBatchTokenizer):
    def __init__(self, *args, **kwargs):
        kwargs['pattern'] = 'Query: {query} Document: {document} Relevant:'
        kwargs['return_attention_mask'] = True
        kwargs['pad_to_max_length'] = True
        kwargs['return_tensors'] = 'pt'
        kwargs['max_length'] = 512
        kwargs['truncation']=True
        super().__init__(*args, **kwargs)

@torch.no_grad()
def greedy_decode(model: PreTrainedModel,
                  input_ids: torch.Tensor,
                  length: int,
                  attention_mask: torch.Tensor = None,
                  return_last_logits: bool = True) -> DecodedOutput:
    decode_ids = torch.full((input_ids.size(0), 1),
                            model.config.decoder_start_token_id,
                            dtype=torch.long).to(input_ids.device)
    past = model.get_encoder()(input_ids, attention_mask=attention_mask)
    next_token_logits = None
    for _ in range(length):
        model_inputs = model.prepare_inputs_for_generation(
            decode_ids,
            past=past,
            attention_mask=attention_mask,
            use_cache=True)
        outputs = model(**model_inputs)  # (batch_size, cur_len, vocab_size)
        next_token_logits = outputs[0][:, -1, :]  # (batch_size, vocab_size)
        decode_ids = torch.cat([decode_ids,
                                next_token_logits.max(1)[1].unsqueeze(-1)],
                               dim=-1)
        past = outputs[1]
    if return_last_logits:
        return decode_ids, next_token_logits
    return decode_ids

class Reranker:
    """Class representing a reranker.
    A reranker takes a list texts and returns a list of texts non-destructively
    (i.e., does not alter the original input list of texts).
    """
    @abc.abstractmethod
    def rerank(self, query: Query, texts: List[Text]) -> List[Text]:
        """Reranks a list of texts with respect to a query.
         Parameters
         ----------
         query : Query
             The query.
         texts : List[Text]
             The list of texts.
         Returns
         -------
         List[Text]
             Reranked list of texts.
         """
        pass

class T5Ranker(Reranker):
    def __init__(self,
                 batch_size: int = 8):
        model_name = 'castorini/monot5-base-msmarco'
        model = T5ForConditionalGeneration.from_pretrained(model_name)
        model = model.to("cpu").eval()
        self.model = model

        tokenizer_name = 't5-base'
        tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
        tokenizer = T5BatchTokenizer(tokenizer, batch_size)
        self.tokenizer = tokenizer
        
        self.device = next(self.model.parameters(), None).device

    def rerank(self, qry: str, txts: List[str]) -> List[Text]:
        query = Query(qry)
        texts = [ Text(p[1], 0) for p in txts]

        batch_input = QueryDocumentBatch(query=query, documents=texts)
        for batch in self.tokenizer.traverse_query_document(batch_input):
            input_ids = batch.output['input_ids'].to(self.device)
            attn_mask = batch.output['attention_mask'].to(self.device)
            _, batch_scores = greedy_decode(self.model,
                                            input_ids,
                                            length=1,
                                            attention_mask=attn_mask,
                                            return_last_logits=True)

            # 6136 and 1176 are the indexes of the tokens false and true in T5.
            batch_scores = batch_scores[:, [6136, 1176]]
            batch_scores = torch.nn.functional.log_softmax(batch_scores, dim=1)
            batch_log_probs = batch_scores[:, 1].tolist()
            for doc, score in zip(batch.documents, batch_log_probs):
                doc.score = score
        return texts

if __name__ == '__main__':

    # batch_size = 8

    # model_name = 'castorini/monot5-base-msmarco'
    # model = T5ForConditionalGeneration.from_pretrained(model_name)
    # model = model.to("cpu").eval()

    # tokenizer_name = 't5-base'
    # tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
    # tokenizer = T5BatchTokenizer(tokenizer, batch_size)

    # reranker =  T5Reranker(model, tokenizer)

    # query = Query('who proposed the geocentric theory')

    # passages = [['7744105', 'For Earth-centered it was  Geocentric Theory proposed by greeks under the guidance of Ptolemy and Sun-centered was Heliocentric theory proposed by Nicolas Copernicus in 16th century A.D. In short, Your Answers are: 1st blank - Geo-Centric Theory. 2nd blank - Heliocentric Theory.'], ['2593796', 'Copernicus proposed a heliocentric model of the solar system â\x80\x93 a model where everything orbited around the Sun. Today, with advancements in science and technology, the geocentric model seems preposterous.he geocentric model, also known as the Ptolemaic system, is a theory that was developed by philosophers in Ancient Greece and was named after the philosopher Claudius Ptolemy who lived circa 90 to 168 A.D. It was developed to explain how the planets, the Sun, and even the stars orbit around the Earth.'], ['6217200', 'The geocentric model, also known as the Ptolemaic system, is a theory that was developed by philosophers in Ancient Greece and was named after the philosopher Claudius Ptolemy who lived circa 90 to 168 A.D. It was developed to explain how the planets, the Sun, and even the stars orbit around the Earth.opernicus proposed a heliocentric model of the solar system â\x80\x93 a model where everything orbited around the Sun. Today, with advancements in science and technology, the geocentric model seems preposterous.'], ['3276925', 'Copernicus proposed a heliocentric model of the solar system â\x80\x93 a model where everything orbited around the Sun. Today, with advancements in science and technology, the geocentric model seems preposterous.Simple tools, such as the telescope â\x80\x93 which helped convince Galileo that the Earth was not the center of the universe â\x80\x93 can prove that ancient theory incorrect.ou might want to check out one article on the history of the geocentric model and one regarding the geocentric theory. Here are links to two other articles from Universe Today on what the center of the universe is and Galileo one of the advocates of the heliocentric model.'], ['6217208', 'Copernicus proposed a heliocentric model of the solar system â\x80\x93 a model where everything orbited around the Sun. Today, with advancements in science and technology, the geocentric model seems preposterous.Simple tools, such as the telescope â\x80\x93 which helped convince Galileo that the Earth was not the center of the universe â\x80\x93 can prove that ancient theory incorrect.opernicus proposed a heliocentric model of the solar system â\x80\x93 a model where everything orbited around the Sun. Today, with advancements in science and technology, the geocentric model seems preposterous.'], ['4280557', 'The geocentric model, also known as the Ptolemaic system, is a theory that was developed by philosophers in Ancient Greece and was named after the philosopher Claudius Ptolemy who lived circa 90 to 168 A.D. It was developed to explain how the planets, the Sun, and even the stars orbit around the Earth.imple tools, such as the telescope â\x80\x93 which helped convince Galileo that the Earth was not the center of the universe â\x80\x93 can prove that ancient theory incorrect. You might want to check out one article on the history of the geocentric model and one regarding the geocentric theory.'], ['264181', 'Nicolaus Copernicus (b. 1473â\x80\x93d. 1543) was the first modern author to propose a heliocentric theory of the universe. From the time that Ptolemy of Alexandria (c. 150 CE) constructed a mathematically competent version of geocentric astronomy to Copernicusâ\x80\x99s mature heliocentric version (1543), experts knew that the Ptolemaic system diverged from the geocentric concentric-sphere conception of Aristotle.'], ['4280558', 'A Geocentric theory is an astronomical theory which describes the universe as a Geocentric system, i.e., a system which puts the Earth in the center of the universe, and describes other objects from the point of view of the Earth. Geocentric theory is an astronomical theory which describes the universe as a Geocentric system, i.e., a system which puts the Earth in the center of the universe, and describes other objects from the point of view of the Earth.'], ['3276926', 'The geocentric model, also known as the Ptolemaic system, is a theory that was developed by philosophers in Ancient Greece and was named after the philosopher Claudius Ptolemy who lived circa 90 to 168 A.D. It was developed to explain how the planets, the Sun, and even the stars orbit around the Earth.ou might want to check out one article on the history of the geocentric model and one regarding the geocentric theory. Here are links to two other articles from Universe Today on what the center of the universe is and Galileo one of the advocates of the heliocentric model.'], ['5183032', "After 1,400 years, Copernicus was the first to propose a theory which differed from Ptolemy's geocentric system, according to which the earth is at rest in the center with the rest of the planets revolving around it."]]

    # texts = [ Text(p[1], 0) for p in passages] # Note, pyserini scores don't matter since T5 will ignore them.

    # # Either option, let's print out the passages prior to reranking:
    # for i in range(0, 10):
    #     print(f'{i+1:2} {texts[i].score:.5f} {texts[i].text}')

    # print('*'*80)

    # # Finally, rerank:
    # reranked = reranker.rerank(query, texts)
    # reranked.sort(key=lambda x: x.score, reverse=True)

    # # Print out reranked results:
    # for i in range(0, 10):
    #     print(f'{i+1:2} {reranked[i].score:.5f} {reranked[i].text}')
    
    #################### Reranker ####################
    reranker =  T5RerankerCopy()
    qry = 'who proposed the geocentric theory'
    txts = [['7744105', 'For Earth-centered it was  Geocentric Theory proposed by greeks under the guidance of Ptolemy and Sun-centered was Heliocentric theory proposed by Nicolas Copernicus in 16th century A.D. In short, Your Answers are: 1st blank - Geo-Centric Theory. 2nd blank - Heliocentric Theory.'], ['2593796', 'Copernicus proposed a heliocentric model of the solar system â\x80\x93 a model where everything orbited around the Sun. Today, with advancements in science and technology, the geocentric model seems preposterous.he geocentric model, also known as the Ptolemaic system, is a theory that was developed by philosophers in Ancient Greece and was named after the philosopher Claudius Ptolemy who lived circa 90 to 168 A.D. It was developed to explain how the planets, the Sun, and even the stars orbit around the Earth.'], ['6217200', 'The geocentric model, also known as the Ptolemaic system, is a theory that was developed by philosophers in Ancient Greece and was named after the philosopher Claudius Ptolemy who lived circa 90 to 168 A.D. It was developed to explain how the planets, the Sun, and even the stars orbit around the Earth.opernicus proposed a heliocentric model of the solar system â\x80\x93 a model where everything orbited around the Sun. Today, with advancements in science and technology, the geocentric model seems preposterous.'], ['3276925', 'Copernicus proposed a heliocentric model of the solar system â\x80\x93 a model where everything orbited around the Sun. Today, with advancements in science and technology, the geocentric model seems preposterous.Simple tools, such as the telescope â\x80\x93 which helped convince Galileo that the Earth was not the center of the universe â\x80\x93 can prove that ancient theory incorrect.ou might want to check out one article on the history of the geocentric model and one regarding the geocentric theory. Here are links to two other articles from Universe Today on what the center of the universe is and Galileo one of the advocates of the heliocentric model.'], ['6217208', 'Copernicus proposed a heliocentric model of the solar system â\x80\x93 a model where everything orbited around the Sun. Today, with advancements in science and technology, the geocentric model seems preposterous.Simple tools, such as the telescope â\x80\x93 which helped convince Galileo that the Earth was not the center of the universe â\x80\x93 can prove that ancient theory incorrect.opernicus proposed a heliocentric model of the solar system â\x80\x93 a model where everything orbited around the Sun. Today, with advancements in science and technology, the geocentric model seems preposterous.'], ['4280557', 'The geocentric model, also known as the Ptolemaic system, is a theory that was developed by philosophers in Ancient Greece and was named after the philosopher Claudius Ptolemy who lived circa 90 to 168 A.D. It was developed to explain how the planets, the Sun, and even the stars orbit around the Earth.imple tools, such as the telescope â\x80\x93 which helped convince Galileo that the Earth was not the center of the universe â\x80\x93 can prove that ancient theory incorrect. You might want to check out one article on the history of the geocentric model and one regarding the geocentric theory.'], ['264181', 'Nicolaus Copernicus (b. 1473â\x80\x93d. 1543) was the first modern author to propose a heliocentric theory of the universe. From the time that Ptolemy of Alexandria (c. 150 CE) constructed a mathematically competent version of geocentric astronomy to Copernicusâ\x80\x99s mature heliocentric version (1543), experts knew that the Ptolemaic system diverged from the geocentric concentric-sphere conception of Aristotle.'], ['4280558', 'A Geocentric theory is an astronomical theory which describes the universe as a Geocentric system, i.e., a system which puts the Earth in the center of the universe, and describes other objects from the point of view of the Earth. Geocentric theory is an astronomical theory which describes the universe as a Geocentric system, i.e., a system which puts the Earth in the center of the universe, and describes other objects from the point of view of the Earth.'], ['3276926', 'The geocentric model, also known as the Ptolemaic system, is a theory that was developed by philosophers in Ancient Greece and was named after the philosopher Claudius Ptolemy who lived circa 90 to 168 A.D. It was developed to explain how the planets, the Sun, and even the stars orbit around the Earth.ou might want to check out one article on the history of the geocentric model and one regarding the geocentric theory. Here are links to two other articles from Universe Today on what the center of the universe is and Galileo one of the advocates of the heliocentric model.'], ['5183032', "After 1,400 years, Copernicus was the first to propose a theory which differed from Ptolemy's geocentric system, according to which the earth is at rest in the center with the rest of the planets revolving around it."]]
    # Either option, let's print out the passages prior to reranking:
    for i in range(0, 10):
        print(f'{i+1:2} {txts[i][0]} {txts[i][1]}')

    print('*'*80)

    # Finally, rerank:
    reranked = reranker.rerank(qry, txts)
    reranked.sort(key=lambda x: x.score, reverse=True)

    # Print out reranked results:
    for i in range(0, 10):
        print(f'{i+1:2} {reranked[i].score:.5f} {reranked[i].text}')