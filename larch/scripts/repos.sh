#!/bin/bash

# Script to build repository database archives from the current state of
# the pacman/sync database on the running system.

# $1 (optional) is the directory within which subdirectories for each
# repository will be built. The default is the current directory.

if [ -z "$1" ]; then
   d="."
else
   d="$1"
fi

for f in core extra community; do
    mkdir -p ${d}/${f}
    echo "Compressing $f db ..."
    tar -czf ${d}/${f}/${f}.db.tar.gz -C /var/lib/pacman/sync/${f} .
done
