ARG VERSION=latest
FROM python:$VERSION

RUN apt-get update \
    && apt-get install -y default-jdk ant

WORKDIR /usr/lib/jvm/default-java/jre/lib
RUN ln -s ../../lib amd64

WORKDIR /usr/src/pylucene
RUN curl https://downloads.apache.org/lucene/pylucene/pylucene-8.3.0-src.tar.gz \
    | tar -xz --strip-components=1
RUN cd jcc \
    && NO_SHARED=1 JCC_JDK=/usr/lib/jvm/default-java python setup.py install
RUN make all install JCC='python -m jcc' ANT=ant PYTHON=python NUM_FILES=8

WORKDIR /usr/src
RUN rm -rf pylucene
RUN pip install tokenizers==0.7 transformers==2.10.0 torch==1.4.0

RUN git clone https://github.com/eddiebarry/WHO-FAQ-Search-Engine.git
WORKDIR /usr/src/WHO-FAQ-Search-Engine