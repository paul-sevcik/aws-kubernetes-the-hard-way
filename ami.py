
from datetime import datetime
import functools

import boto3

__all__ = ["get_ami"]


def _get_aws_account_id():
    sts = boto3.client('sts')
    response = sts.get_caller_identity()
    return response['Account']


def get_latest_ami(ami_name):
    ec2 = boto3.client('ec2')

    ownerid = _get_aws_account_id()

    response = ec2.describe_images(
        Owners=[ownerid],
        Filters=[
            {
                'Name': 'name',
                'Values': ['kube-{}*'.format(ami_name)],
            }
        ],
    )
    images = response['Images']

    most_recent_ami = None
    most_recent_creation = datetime.min

    for image in images:
        creation_date = datetime.strptime(image['CreationDate'], '%Y-%m-%dT%H:%M:%S.%fZ')
        if creation_date > most_recent_creation:
            most_recent_ami = image
            most_recent_creation = creation_date

    if most_recent_ami == None:
        raise LookupError("no AMIs matching 'kube-{}*'".format(ami_name))

    return most_recent_ami

@functools.lru_cache(maxsize=32)
def get_ami(ami_name):
    import json
    with open('ami/{}.ami'.format(ami_name)) as manifest_file:
        manifest = json.load(manifest_file)

    amis = [build['artifact_id'].split(':') for build in manifest['builds']]
    assert len(amis) == 1 and amis[0][0] == 'us-west-2', amis

    return amis[0][1]
