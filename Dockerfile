FROM ubuntu:20.04

RUN apt-get update && apt-get upgrade -y && apt-get clean

RUN apt-get install -y curl python3 python3-dev python3-distutils python3-pip git wget

RUN pip3 install astropy pysynphot scipy numpy matplotlib h5py scikit-learn notebook pandas

RUN apt-get install vim -y

RUN ln -s /usr/bin/python3 /usr/bin/python

# Galaxia

RUN git clone https://github.com/jluastro/galaxia.git

RUN mkdir /galaxia_models
WORKDIR /galaxia_models
RUN wget http://bhs.astro.berkeley.edu/GalaxiaData.tar.gz
RUN tar -xvf GalaxiaData.tar.gz && rm GalaxiaData.tar.gz

WORKDIR /galaxia
RUN ./configure --prefix=/bin/galaxia
RUN make
RUN make install

RUN echo "export PATH=/bin/galaxia/bin:$PATH" >> ~/.bashrc

# Popsycle

RUN export PYTHONPATH=$PYTHONPATH:/PopSyCLE

WORKDIR /

RUN git clone https://github.com/NolanSmyth/PopSyCLE.git

ENV PYTHONPATH "${PYTHONPATH}:/PopSyCLE/"

# Add SPISEA

RUN export PYTHONPATH=$PYTHONPATH:/SPISEA

RUN cd / && git clone https://github.com/astropy/SPISEA.git

ENV PYTHONPATH "${PYTHONPATH}:/SPISEA/"

# Add data to cdbs folder
RUN mkdir /cdbs
WORKDIR /cdbs
RUN wget https://archive.stsci.edu/hlsps/reference-atlases/hlsp_reference-atlases_hst_multi_everything_multi_v10_sed.tar
RUN wget https://archive.stsci.edu/hlsps/reference-atlases/hlsp_reference-atlases_hst_multi_star-galaxy-models_multi_v3_synphot2.tar
RUN tar -xvf hlsp_reference-atlases_hst_multi_everything_multi_v10_sed.tar && rm hlsp_reference-atlases_hst_multi_everything_multi_v10_sed.tar
RUN tar -xvf hlsp_reference-atlases_hst_multi_star-galaxy-models_multi_v3_synphot2.tar && rm hlsp_reference-atlases_hst_multi_star-galaxy-models_multi_v3_synphot2.tar

# Move data folders to cdbs
RUN mv /cdbs/grp/redcat/trds/comp /cdbs
RUN mv /cdbs/grp/redcat/trds/mtab /cdbs
RUN mv /cdbs/grp/redcat/trds/grid /cdbs

RUN mkdir /cdbs/models
WORKDIR /cdbs/models
RUN wget http://astro.berkeley.edu/~jlu/spisea/spisea_models.tar.gz && wget http://astro.berkeley.edu/~jlu/spisea/spisea_cdbs.tar.gz
RUN tar -xvf spisea_cdbs.tar.gz && tar -xvf spisea_models.tar.gz && rm spisea_cdbs.tar.gz && rm spisea_models.tar.gz

ENV PYSYN_CDBS /cdbs/models/cdbs/
ENV SPISEA_MODELS /cdbs/models

WORKDIR /