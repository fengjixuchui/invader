#!/bin/bash

if [[ $EUID -ne 0 ]]; then
   echo "[!] This script must be run as root" 1>&2
   exit 1
fi

IFS='/' read -a array <<< pwd

if [[ "$(pwd)" != *setup ]]
then
	cd ./setup
fi

# reset the database
if [ -e ../data/Invader.db ]
then
	rm ../data/Invader.db
fi

python ./setup_database.py
cd ..

# remove the debug file if it exists
if [ -e Invader.debug ]
then
	rm Invader.debug
fi

# remove the download folders
if [ -d ./downloads/ ]
then
	rm -rf ./downloads/
fi

# start up Invader if not in docker otherwise return
if [ -f /.dockerenv ]; then
    echo "\033[1;32m[*] Invader reset complete returning back to Docker\033[0m"
else
    ./Invader
fi
