#!/usr/bin/env bash

while true; do curl -H 'Authorization: token
22339bcf02f223f756bfd1f58ff07a609cd52367' -H 'Accept: application/vnd.github.v3.raw' -O -L https://api.github.com/repos/bjd2385/error_codes/contents/time.py &>/dev/null; sleep 5; done &
