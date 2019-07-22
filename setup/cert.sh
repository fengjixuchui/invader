#!/bin/bash

# generate a self-signed CERT
#openssl genrsa -des3 -out ./data/Invader.orig.key 2048
#openssl rsa -in ./data/Invader.orig.key -out ./data/Invader.key
#openssl req -new -key ./data/Invader.key -out ./data/Invader.csr
#openssl x509 -req -days 365 -in ./data/Invader.csr -signkey ./data/Invader.key -out ./data/Invader.crt

#openssl req -new -x509 -keyout ../data/Invader-priv.key -out ../data/Invader-chain.pem -days 365 -nodes
openssl req -new -x509 -keyout ../data/Invader-priv.key -out ../data/Invader-chain.pem -days 365 -nodes -subj "/C=US" >/dev/null 2>&1

echo -e "\033[1;32m[*] Certificate written to ../data/Invader-chain.pem"
echo -e "[*] Private key written to ../data/Invader-priv.key\033[0m"
