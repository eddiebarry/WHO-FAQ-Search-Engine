# Search Engine

## A search engine based on Pylucene
## Stores data in different fields

### Data definition
```
Json files can be added to the index if they follow the following format
{
  "id": "doc1",
  "contents": "contents of doc one.",
  "keywords": "Vaccine 1",
  "Disease": "Disease 1",
  
  ...
}
```

### To run
```
docker build --tag lucene_test .
docker run -it lucene_test /bin/bash
```

### Test the code
```
python integration_test.py
```

### For an example of how the search engine works, see
integration_test.py

### Special thanks to
- The [pygaggle](https://github.com/castorini/pygaggle) project especially their MSMarcoRerankin [paper](https://arxiv.org/pdf/2003.06713.pdf)