#!/bin/bash

# Install nuitka if needed
#pip3 install -U nuitka

# Build
python3 -m nuitka --standalone --python-flag=no_site --remove-output spotrec.py

# Package
VERSION=$(awk '{if(/app_version = /) print $3}' spotrec.py | tr -d '"')
FILENAME=spotrec-$VERSION-standalone.tar.gz
tar -zcvf $FILENAME spotrec.dist/

echo
echo "SHA256SUM:"
echo $(sha256sum $FILENAME)
