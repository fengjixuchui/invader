#!/bin/bash

# MIT License

# Copyright (C) 2019, Entynetproject. All Rights Reserved.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# generate a self-signed CERT
# openssl genrsa -des3 -out ./data/invader.orig.key 2048
# openssl rsa -in ./data/invader.orig.key -out ./data/invader.key
# openssl req -new -key ./data/invader.key -out ./data/invader.csr
# openssl x509 -req -days 365 -in ./data/invader.csr -signkey ./data/invader.key -out ./data/invader.crt

# openssl req -new -x509 -keyout ../data/invader-priv.key -out ../data/invader-chain.pem -days 365 -nodes
openssl req -new -x509 -keyout ../data/invader-priv.key -out ../data/invader-chain.pem -days 365 -nodes -subj "/C=US" >/dev/null 2>&1

echo -e "\033[1;32m[*] Certificate written to ../data/invader-chain.pem"
echo -e "[*] Private key written to ../data/invader-priv.key\033[0m"
