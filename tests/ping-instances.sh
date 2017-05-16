#!/bin/bash

# FIXME: invalid hosts report successful pings
for host in controller{0..2} worker{0..2}; do
    hostname=$(aws ec2 describe-instances --filter Name=tag:aws:cloudformation:logical-id,Values=worker1 --query 'Reservations[*].Instances[*].NetworkInterfaces[*].Association.PublicDnsName'  --output text)
    for ip in 10.240.0.{1{0..2},2{0..2}}; do
        if ! ssh -o CheckHostIP=no ubuntu@$hostname ping -c 1 $ip > /dev/null 2>&1; then
            echo "$host failed to ping $ip"
        else
            echo "$host pinged $ip"
        fi
    done
done
