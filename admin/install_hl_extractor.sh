#!/bin/sh

if [ $# -eq 1 ]
  then
    APP_DIR=$1
else
    APP_DIR=$(dirname $0)/..
    echo "Application directory is not specified. Using default: '$APP_DIR'!"
fi

# Installing dependencies
apt-get -y install build-essential libyaml-dev libfftw3-dev libavcodec-dev \
    libavformat-dev python-dev python-numpy-dev python-numpy git \
    libsamplerate0-dev libtag1-dev libqt4-dev swig pkg-config

# Gaia
# See https://github.com/MTG/gaia
git clone https://github.com/MTG/gaia.git /tmp/gaia
cd /tmp/gaia
./waf configure --download --with-python-bindings
./waf
./waf install

# Essentia
# See http://essentia.upf.edu/documentation/installing.html
git clone https://github.com/MTG/essentia.git /tmp/essentia
cd /tmp/essentia
./waf configure --mode=release --with-gaia --with-example=streaming_extractor_music_svm
./waf
cp /tmp/essentia/build/src/examples/streaming_extractor_music_svm \
    $APP_DIR/high-level/streaming_extractor_music_svm

# SVM models
mkdir /tmp/models
cd /tmp/models
curl --silent -o models.tar.gz http://essentia.upf.edu/documentation/svm_models/essentia-extractor-svm_models-v2.1_beta1.tar.gz
tar -xvzf models.tar.gz
mv /tmp/models/v2.1_beta1/svm_models $APP_DIR/hl_extractor

# Cleanup
rm -rf /tmp/gaia
rm -rf /tmp/essentia
