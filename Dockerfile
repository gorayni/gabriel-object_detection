FROM cmusatyalab/gabriel

WORKDIR /
RUN git clone https://github.com/gorayni/gabriel-object_detection.git

ENV FASTER_RCNN_ROOT /py-faster-rcnn

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \    
    libopencv-dev \
    libatlas-base-dev \
    libhdf5-serial-dev \
    libldap2-dev \
    libleveldb-dev \
    libprotobuf-dev \
    libsasl2-dev \
    libsnappy-dev \
    libsnmp-dev \
    libssl-dev \
    nano \
    protobuf-compiler \
    python-dev \
    python-matplotlib \
    python-opencv \
    wget && \
    apt-get install -y --no-install-recommends libboost-all-dev && \
    apt-get install -y apt-utils libgflags-dev libgoogle-glog-dev liblmdb-dev && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists/*

# fix bug for hdf5 for Caffe. See https://github.com/NVIDIA/DIGITS/issues/156
RUN cd /usr/lib/x86_64-linux-gnu && ln -s libhdf5_serial.so libhdf5.so && \
    ln -s libhdf5_serial_hl.so libhdf5_hl.so

# Install pip
RUN curl -O https://bootstrap.pypa.io/get-pip.py && \
    python get-pip.py && \
    rm get-pip.py
RUN pip install -U pip setuptools

# download py-faster-rcnn
WORKDIR /
RUN git clone --recursive https://github.com/rbgirshick/py-faster-rcnn.git

# install python dependencies
WORKDIR /py-faster-rcnn/caffe-fast-rcnn
RUN pip install easydict && \
    pip install cython
RUN cat python/requirements.txt | xargs -n1 pip2 install --user

# must be this version of numpy, or it will crash: https://github.com/rbgirshick/py-faster-rcnn/issues/480; no need for this anymore?
RUN pip install --user -Iv numpy
RUN pip install --user -U python-dateutil

# compile py-faster-rcnn
WORKDIR /py-faster-rcnn
RUN cd lib && \
    make -j$(nproc)
RUN cd caffe-fast-rcnn && \
    cp Makefile.config.example Makefile.config && \
    sed -i 's%/usr/lib/python2.7/dist-packages/numpy/core/include%/usr/local/lib/python2.7/dist-packages/numpy/core/include%' Makefile.config && \
    sed -i 's%INCLUDE_DIRS := $(PYTHON_INCLUDE) /usr/local/include%INCLUDE_DIRS := $(PYTHON_INCLUDE) /usr/local/include /usr/include/hdf5/serial/%' Makefile.config && \
    sed -i 's%LIBRARY_DIRS := $(PYTHON_LIB) /usr/local/lib /usr/lib%LIBRARY_DIRS := $(PYTHON_LIB) /usr/local/lib /usr/lib /usr/lib/x86_64-linux-gnu/hdf5/serial/%' Makefile.config && \
    sed -i 's%# WITH_PYTHON_LAYER := 1%WITH_PYTHON_LAYER := 1%' Makefile.config && \
    sed -i 's%# CPU_ONLY := 1%CPU_ONLY := 1%' Makefile.config && \
    cat Makefile.config && \
    make -j$(nproc) && \
    make -j$(nproc) pycaffe

# download/extract model for sandwich
WORKDIR /gabriel-object_detection/model
RUN wget https://raw.githubusercontent.com/rbgirshick/py-faster-rcnn/master/models/coco/VGG16/faster_rcnn_end2end/test.prototxt
RUN wget https://dl.dropboxusercontent.com/s/cotx0y81zvbbhnt/coco_vgg16_faster_rcnn_final.caffemodel

EXPOSE 7070 9098 9111 22222
CMD ["bash", "-c", "gabriel-control -d -n eth0 -l & sleep 5; gabriel-ucomm -s 127.0.0.1:8021 & sleep 5; cd /gabriel-object_detection && python proxy.py -s 127.0.0.1:8021"]
