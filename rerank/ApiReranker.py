import requests
import json, os, pdb
from typing import List, Mapping, Tuple, Union, Iterable, Optional, Any
# Importing constants
from dotenv import load_dotenv
load_dotenv()

class ApiReranker():
    def __init__(
            self,
            endpoint = os.getenv("RE_RANK_ENDPOINT")+"/api/v1/reranking",
            cache_endpoint = os.getenv("RE_RANK_ENDPOINT")+"/api/v1/reranking-cache",
        ):
        self.endpoint = endpoint
        self.cache_endpoint = cache_endpoint
        # self.session = requests.Session()

    def rerank(self, qry: str, txts: List[str]) -> List[Any]:
        params = {
            "query": qry,
            "texts": txts,
        }

        # check in cache
        response = requests.get(self.cache_endpoint, json=json.dumps(params))
        if response.status_code == 210 or response.status_code == 429:
            # check in actual
            response = requests.get(self.endpoint, json=json.dumps(params))
            if response.status_code != 200:
                return False
        
        scoreDocs = response.json()['scoreDocs']
        return scoreDocs


if __name__ == '__main__':    
    from rerank_config import RE_RANK_ENDPOINT
    #################### Reranker ####################
    reranker =  ApiReranker()
    qry = 'who proposed the geocentric theory'
    txts = [['7744105', 'For Earth-centered it was  Geocentric Theory proposed by greeks under the guidance of Ptolemy and Sun-centered was Heliocentric theory proposed by Nicolas Copernicus in 16th century A.D. In short, Your Answers are: 1st blank - Geo-Centric Theory. 2nd blank - Heliocentric Theory.'], ['2593796', 'Copernicus proposed a heliocentric model of the solar system â\x80\x93 a model where everything orbited around the Sun. Today, with advancements in science and technology, the geocentric model seems preposterous.he geocentric model, also known as the Ptolemaic system, is a theory that was developed by philosophers in Ancient Greece and was named after the philosopher Claudius Ptolemy who lived circa 90 to 168 A.D. It was developed to explain how the planets, the Sun, and even the stars orbit around the Earth.'], ['6217200', 'The geocentric model, also known as the Ptolemaic system, is a theory that was developed by philosophers in Ancient Greece and was named after the philosopher Claudius Ptolemy who lived circa 90 to 168 A.D. It was developed to explain how the planets, the Sun, and even the stars orbit around the Earth.opernicus proposed a heliocentric model of the solar system â\x80\x93 a model where everything orbited around the Sun. Today, with advancements in science and technology, the geocentric model seems preposterous.'], ['3276925', 'Copernicus proposed a heliocentric model of the solar system â\x80\x93 a model where everything orbited around the Sun. Today, with advancements in science and technology, the geocentric model seems preposterous.Simple tools, such as the telescope â\x80\x93 which helped convince Galileo that the Earth was not the center of the universe â\x80\x93 can prove that ancient theory incorrect.ou might want to check out one article on the history of the geocentric model and one regarding the geocentric theory. Here are links to two other articles from Universe Today on what the center of the universe is and Galileo one of the advocates of the heliocentric model.'], ['6217208', 'Copernicus proposed a heliocentric model of the solar system â\x80\x93 a model where everything orbited around the Sun. Today, with advancements in science and technology, the geocentric model seems preposterous.Simple tools, such as the telescope â\x80\x93 which helped convince Galileo that the Earth was not the center of the universe â\x80\x93 can prove that ancient theory incorrect.opernicus proposed a heliocentric model of the solar system â\x80\x93 a model where everything orbited around the Sun. Today, with advancements in science and technology, the geocentric model seems preposterous.'], ['4280557', 'The geocentric model, also known as the Ptolemaic system, is a theory that was developed by philosophers in Ancient Greece and was named after the philosopher Claudius Ptolemy who lived circa 90 to 168 A.D. It was developed to explain how the planets, the Sun, and even the stars orbit around the Earth.imple tools, such as the telescope â\x80\x93 which helped convince Galileo that the Earth was not the center of the universe â\x80\x93 can prove that ancient theory incorrect. You might want to check out one article on the history of the geocentric model and one regarding the geocentric theory.'], ['264181', 'Nicolaus Copernicus (b. 1473â\x80\x93d. 1543) was the first modern author to propose a heliocentric theory of the universe. From the time that Ptolemy of Alexandria (c. 150 CE) constructed a mathematically competent version of geocentric astronomy to Copernicusâ\x80\x99s mature heliocentric version (1543), experts knew that the Ptolemaic system diverged from the geocentric concentric-sphere conception of Aristotle.'], ['4280558', 'A Geocentric theory is an astronomical theory which describes the universe as a Geocentric system, i.e., a system which puts the Earth in the center of the universe, and describes other objects from the point of view of the Earth. Geocentric theory is an astronomical theory which describes the universe as a Geocentric system, i.e., a system which puts the Earth in the center of the universe, and describes other objects from the point of view of the Earth.'], ['3276926', 'The geocentric model, also known as the Ptolemaic system, is a theory that was developed by philosophers in Ancient Greece and was named after the philosopher Claudius Ptolemy who lived circa 90 to 168 A.D. It was developed to explain how the planets, the Sun, and even the stars orbit around the Earth.ou might want to check out one article on the history of the geocentric model and one regarding the geocentric theory. Here are links to two other articles from Universe Today on what the center of the universe is and Galileo one of the advocates of the heliocentric model.'], ['5183032', "After 1,400 years, Copernicus was the first to propose a theory which differed from Ptolemy's geocentric system, according to which the earth is at rest in the center with the rest of the planets revolving around it."]]
    
    # Either option, let's print out the passages prior to reranking:
    for i in range(0, 10):
        print(f'{i+1:2} {txts[i][0]} {txts[i][1]}')

    print('*'*80)

    # Finally, rerank:
    scoreDocs = reranker.rerank(qry, txts)

    # Print out reranked results:
    for i in range(0, 10):
        print(f'{i+1:2} {scoreDocs[i][0]:.5f} {scoreDocs[i][1]}')