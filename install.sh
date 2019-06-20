#! /bin/sh

echo 'Compiling and Installing the Tello Video Stream module'
echo 'Python default version is 3.6, change the script if you are using another one'

py_version=3.6

gitrep_location=$(pwd)
sudo apt-get update -y

# install cmake
# Doubt with pip / pip3
sudo pip3 install cmake

# install dependencies
sudo apt-get install libboost-all-dev -y
sudo apt-get install libavcodec-dev -y
sudo apt-get install libswscale-dev -y
sudo apt-get install python-numpy -y
sudo apt-get install python-matplotlib -y
sudo pip3 install opencv-python
sudo apt-get install python-imaging-tk

#Configure boost3
#Using https://stackoverflow.com/questions/46374747/cmake-3-9-3-cannot-find-boost1-65-1-boost-python#answers-header

sudo apt-get install unzip -y
sudo apt-get install wget -y
sudo apt-get update -y

wget https://dl.bintray.com/boostorg/release/1.70.0/source/boost_1_70_0.tar.gz
unzip boost_1_70_0.tar.gz -d /usr/local
sudo cp /usr/local/boost_1_70_0/tools/build/example/user-config.jam $HOME/user-config.jam

# Adapt to specific python you are using
sed -i 's/python3.1/python${py_version}/g' $HOME/user-config.jam
sed -i 's/python : 3.1/python : ${py_version}/g' $HOME/user-config.jam
#Building boost
cd /usr/local/boost_1_70_0
./bootstrap.sh --prefix=/usr/local --with-python=python3
./b2 --install -j 8

# Check for .profile file
FILE=$HOME/.profile
if ! test -f "$FILE"; then
    echo "$FILE should exist ..."
    exit 1
fi
echo "" >> $HOME/.profile
echo "export INCLUDE=\"/usr/local/include/boost:$INCLUDE\"" >> $HOME/.profile
echo "export LIBRARY_PATH=\"/usr/local/lib:$LIBRARY_PATH\"" >> $HOME/.profile
echo "export LD_LIBRARY_PATH=\"/usr/local/lib:$LD_LIBRARY_PATH\"" >> $HOME/.profile

# Just in case ...
export INCLUDE="/usr/local/include/boost:$INCLUDE"
export LIBRARY_PATH="/usr/local/lib:$LIBRARY_PATH"
export LD_LIBRARY_PATH="/usr/local/lib:$LD_LIBRARY_PATH"

# pull and build h264 decoder library
cd $gitrep_location
cd h264decoder
mkdir build
cd build
cmake ..
make

# copy source .so file to tello.py directory
cp libh264decoder.so ../../

echo 'Compilation and Installation Done!'
