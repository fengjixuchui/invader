#!/bin/bash

# generate a self-signed CERT
#openssl genrsa -des3 -out ./data/invader.orig.key 2048
#openssl rsa -in ./data/invader.orig.key -out ./data/invader.key
#openssl req -new -key ./data/invader.key -out ./data/invader.csr
#openssl x509 -req -days 365 -in ./data/invader.csr -signkey ./data/invader.key -out ./data/invader.crt

#openssl req -new -x509 -keyout ../data/invader-priv.key -out ../data/invader-chain.pem -days 365 -nodes
openssl req -new -x509 -keyout ../data/invader-priv.key -out ../data/invader-chain.pem -days 365 -nodes -subj "/C=US" >/dev/null 2>&1

echo -e "[*] Certificate written to ../data/invader-chain.pem\n"
echo -e "[*] Private key written to ../data/invader-priv.key\n"
