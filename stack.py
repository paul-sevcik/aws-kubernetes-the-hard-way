"""
Use Cloudformation to create all VPC elements, including InternetGateway,
RouteTable, and Subnet.
"""
import argparse
from functools import reduce
import logging
import os

import boto3
import yaml

from ami import get_ami

CONTROLLER_INSTANCES = 3
WORKER_INSTANCES = 3

INSTANCES = []
INSTANCES.extend([
    {
        'name': 'controller{0}'.format(num),
        'ami_id': get_ami('controller'),
        'privateip': '10.240.0.{0}'.format(10 + num),
        'source_dest_check': False,
    }
    for num in range(CONTROLLER_INSTANCES)
])

INSTANCES.extend([
    {
        'name': 'worker{0}'.format(num),
        'ami_id': get_ami('worker'),
        'privateip': '10.240.0.{0}'.format(20 + num),
        'source_dest_check': True,
    }
    for num in range(WORKER_INSTANCES)
])


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

    # combine files into final template
    resources = {}
    for template_filename in resource_templates:
        with open(template_filename) as template_file:
            template = yaml.load(template_file)
            for key, value in template.items():
                resources[key] = value
    for format_params in INSTANCES:
        assert format_params['ami_id']
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
            {'ParameterKey': 'InstanceKeyPair', 'ParameterValue': 'kubernetes-on-aws'},
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
    log.debug('deleting the stack')
    cloudformation.delete_stack(StackName=stackname)

    waiter = cloudformation.get_waiter('stack_delete_complete')
    waiter.wait(StackName=stackname)

    log.debug('stack deletion complete')


def instances():
    return sorted([instance['name'] for instance in INSTANCES])


def ssh(cloudformation, stackname, instance_name, ssh_cmd):
    """
        ssh to an ec2 instance
    """
    stack_resources = cloudformation.describe_stack_resources(StackName=stackname)['StackResources']
    instance_ids = [
        resource['PhysicalResourceId']
        for resource in stack_resources
        if resource['ResourceType'] == 'AWS::EC2::Instance'
    ]
    ec2 = boto3.client('ec2')
    reservations = ec2.describe_instances(InstanceIds=instance_ids)['Reservations']
    ec2_instances = reduce(
        lambda x, y: x+y,
        [reservation['Instances'] for reservation in reservations]
    )

    dnsname = None
    for instance in ec2_instances:
        short_name = [tag['Value'] for tag in instance['Tags'] if tag['Key'] == 'aws:cloudformation:logical-id'][0]
        if short_name == instance_name:
            dnsname = instance['PublicDnsName']
            break
    if not dnsname:
        raise RuntimeError('could not find instance for ssh')

    cmd = 'ssh -i {}/.ssh/kubernetes-on-aws'.format(os.environ['HOME']).split()
    cmd.extend('-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no'.split())
    cmd.extend('ubuntu@{}'.format(dnsname).split())
    if ssh_cmd:
        cmd.extend(ssh_cmd.split())
    os.execlp(cmd[0], *cmd)


if __name__ == '__main__':
    log = logging.getLogger('kubernetes-on-aws')
    log.addHandler(logging.StreamHandler())
    log.setLevel(logging.WARNING)

    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose logging')

    subparsers = parser.add_subparsers(dest='command')

    subparsers.add_parser('create', help='create a new stack')
    subparsers.add_parser('delete', help='delete the stack')
    subparsers.add_parser('update', help='update the stack')
    subparsers.add_parser('instances', help='list the aws instances')

    parser_ssh = subparsers.add_parser('ssh', help='ssh to instance')
    parser_ssh.add_argument('instance', choices=sorted([instance['name'] for instance in INSTANCES]))
    parser_ssh.add_argument('ssh_cmd', nargs='?')

    args = parser.parse_args()

    if args.verbose:
        log.setLevel(logging.DEBUG)

    client = boto3.client('cloudformation')
    name = 'Kubernetes-in-AWS'

    if args.command == 'create':
        create(client, name)
    elif args.command == 'update':
        update(client, name)
    elif args.command == 'delete':
        delete(client, name)
    elif args.command == 'instances':
        for instance in instances():
            print(instance)
    elif args.command == 'ssh':
        ssh(client, name, args.instance, args.ssh_cmd)
    else:
        parser.print_help()
