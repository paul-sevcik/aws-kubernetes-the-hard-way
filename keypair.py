
import argparse
import os

import boto3


def create(ec2, name, filename):
    response = ec2.create_key_pair(KeyName=name)
    assert response['KeyName'] == name

    with open(filename, 'w') as keyfile:
        keyfile.write(response['KeyMaterial'])
        keyfile.write('\n')


def delete(ec2, name, filename):
    response = ec2.delete_key_pair(KeyName=name)
    assert response['ResponseMetadata']['HTTPStatusCode'] == 200

    os.remove(filename)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('keypair_cmd', choices=['create', 'delete'])
    args = parser.parse_args()

    client = boto3.client('ec2')
    keyname = 'kubernetes-on-aws'
    private_keyfile = 'kubernetes-on-aws'

    if args.keypair_cmd == 'create':
        create(client, keyname, private_keyfile)
    elif args.keypair_cmd == 'delete':
        delete(client, keyname, private_keyfile)
    else:
        parser.print_help()
