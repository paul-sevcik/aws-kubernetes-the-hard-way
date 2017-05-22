#!/bin/bash

SSH='ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -q'
CMD='sudo /usr/local/bin/goss -g /usr/local/etc/goss.yaml validate'

# Using a single loop caused conflict between the "| while read" and the ssh
# command (the while loop would exececute once).  Not sure why that was a
# problem, but  using a second loop for the ssh fixes it.
names=()
dnsnames=()
while read line; do
    names+=($(echo ${line} | awk '{print $1}'))
    dnsnames+=($(echo ${line} | awk '{print $2}'))
done < <(python stack.py names)

for index in "${!names[@]}"
do
    name=${names[${index}]}
    dnsname=${dnsnames[${index}]}

    if ${SSH} ubuntu@${dnsname} ${CMD}; then
        echo "${name}: testing complete"
    else
        echo "${name}: testing failed"
    fi
done
