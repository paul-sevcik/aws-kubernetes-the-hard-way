"""
Use Cloudformation to create all VPC elements, including InternetGateway,
RouteTable, and Subnet.
"""
import argparse
import base64
from functools import reduce
import logging

import boto3
import yaml

from ami import get_ami

CONTROLLER_INSTANCES = 3
WORKER_INSTANCES = 3


def encode_base64(content):
    """
    Encode contents of a file as base64 string.
    """

    # convert to bytes
    unencoded = bytes(content, 'utf-8')

    # encode as base 64
    encoded = base64.b64encode(unencoded)

    # convert back to string
    data = encoded.decode()

    return data


def get_cert(certfile):
    """
    Encode contents of cert file as base 64.
    """
    with open(certfile) as f:
        unencoded = f.read()
        data = encode_base64(unencoded)
    return data


def build_template():

    # break the template into separate files to make it easier to understand
    resource_templates = [
        'resources/vpc.yaml',
        'resources/internet-gateway.yaml',
        'resources/route-table.yaml',
        'resources/subnet.yaml',
        'resources/security.yaml',
        'resources/elb.yaml',
    ]

    instances = []
    instances.extend([
        {
            'name': 'controller{0}'.format(num),
            'ami_id': get_ami('controller'),
            'privateip': '10.240.0.{0}'.format(10 + num),
            'source_dest_check': False,
        }
        for num in range(CONTROLLER_INSTANCES)
        ])

    instances.extend([
        {
            'name': 'worker{0}'.format(num),
            'ami_id': get_ami('worker'),
            'privateip': '10.240.0.{0}'.format(20 + num),
            'source_dest_check': True,
        }
        for num in range(WORKER_INSTANCES)
        ])

    # combine files into final template
    resources = {}
    for template_filename in resource_templates:
        with open(template_filename) as template_file:
            template = yaml.load(template_file)
            for key, value in template.items():
                resources[key] = value
    for format_params in instances:
        with open('resources/instance.yaml') as template_file:
            template = yaml.load(template_file.read().format(**format_params))
            for key, value in template.items():
                resources[key] = value
    assert len(resources) > 0

    parameters = yaml.load(open('parameters.yaml'))
    vpc_template = {
        'Description': 'private VPC for kubernetes cluster',
        'Parameters': parameters,
        'Resources': resources,
    }

    # now create the stack using our template
    data = yaml.dump(vpc_template, default_flow_style=False)
    log.debug('length of template data = {}'.format(len(data)))

    return data


def getmyip():
    """
    Get public ip address using: http://api.ipaddress.com/myip
    """
    from urllib.request import urlopen

    with urlopen('http://api.ipaddress.com/myip') as url:
        ipaddress = url.read().decode()

    return ipaddress


def apply_template(cloudformation, stackname, create_stack=True):
    if create_stack:
        cf_func = cloudformation.create_stack
        cf_waiter = 'stack_create_complete'
    else:
        cf_func = cloudformation.update_stack
        cf_waiter = 'stack_update_complete'

    template = build_template()
    log.debug('{} the stack'.format('create' if create_stack else 'update'))
    stack = cf_func(
        StackName=stackname,
        TemplateBody=template,
        Parameters=[
            {'ParameterKey': 'InstanceKeyPair', 'ParameterValue': 'paul.sevcik'},
            {'ParameterKey': 'MyIP', 'ParameterValue': getmyip()},
        ]
    )

    # wait for all AWS objects to get applied
    log.debug('wait for {} to finish'.format('create' if create_stack else 'update'))
    stackid = stack['StackId']
    waiter = cloudformation.get_waiter(cf_waiter)
    waiter.wait(StackName=stackid)

    log.debug('{} is done'.format('create' if create_stack else 'update'))


def create(cloudformation, stackname):
    print('creating the stack')
    apply_template(cloudformation, stackname)
    print('stack creation complete')


def update(cloudformation, stackname):
    print('updating the stack')
    apply_template(cloudformation, stackname, create_stack=False)
    print('stack update complete')


def delete(cloudformation, stackname):
    print('deleting the stack')
    cloudformation.delete_stack(StackName=stackname)

    waiter = cloudformation.get_waiter('stack_delete_complete')
    waiter.wait(StackName=stackname)

    print('stack deletion complete')


def names(cloudformation, stackname):
    """
        print out the instances public dns entries
    """
    stack_resources = cloudformation.describe_stack_resources(StackName=stackname)['StackResources']
    instance_ids = [
        resource['PhysicalResourceId']
        for resource in stack_resources
        if resource['ResourceType'] == 'AWS::EC2::Instance'
    ]
    ec2 = boto3.client('ec2')
    reservations = ec2.describe_instances(InstanceIds=instance_ids)['Reservations']
    instances = reduce(
        lambda x, y: x+y,
        [reservation['Instances'] for reservation in reservations]
    )

    for instance in instances:
        name = [tag['Value'] for tag in instance['Tags'] if tag['Key'] == 'aws:cloudformation:logical-id'][0]
        print('{} {}'.format(name, instance['PublicDnsName']))


if __name__ == '__main__':
    log = logging.getLogger('kubernetes-on-aws')
    log.addHandler(logging.StreamHandler())
    log.setLevel(logging.WARNING)

    commands = ['create', 'delete', 'update', 'names']
    parser = argparse.ArgumentParser()
    parser.add_argument('cmd', help='command to run, one of %s' % ' '.join(commands))
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose logging')
    args = parser.parse_args()

    if args.verbose:
        log.setLevel(logging.DEBUG)

    if args.cmd not in commands:
        import sys
        parser.print_help()
        sys.exit(1)

    command_func = locals()[args.cmd]
    command_func(boto3.client('cloudformation'), 'Kubernetes-in-AWS')
