#!/bin/bash

# This script is made for building on Arch-based distributions


# Install Nuitka
package="nuitka"
if pacman -Qs $package > /dev/null ; then
  echo "$package is already installed"
else
  echo "Will need to install $package"
  sudo pacman -S --noconfirm $package
fi

# Build
/usr/bin/nuitka3 spotrec.py

# Remove bin directory
rm -r spotrec.build/

# Rename binary
mv spotrec.bin spotrec

echo "SHA256SUM:"
echo $(sha256sum spotrec)
