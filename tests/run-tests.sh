#!/bin/bash
set -x

fail() {
    exit 1
}
trap "fail" INT TERM

result=0
for instance in $(python stack.py instances)
do
    python stack.py ssh ${instance} "sudo /usr/local/bin/goss -g /usr/local/etc/goss.yaml validate"
    if [[ $? != 0 ]]; then
        result=1
    fi
done
exit $result
