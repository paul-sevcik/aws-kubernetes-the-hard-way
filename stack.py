"""
Use Cloudformation to create all VPC elements, including InternetGateway,
RouteTable, and Subnet.
"""
import argparse
from functools import reduce
import base64

import boto3
import yaml

import s3

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


def get_userdata(**format_params):
    """
    Get user-data, format according to format_args, then encode it as base 64.
    """
    with open(format_params['userdata_template']) as f:
        unencoded = f.read().format(**format_params)
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

    certs = {
        'ca_pem': get_cert('ca/ca.pem'),
        'ca_key_pem': get_cert('ca/ca-key.pem'),
        'kube_proxy_pem': get_cert('ca/kube-proxy.pem'),
        'kube_proxy_key_pem': get_cert('ca/kube-proxy-key.pem'),
        'kubernetes_pem': get_cert('ca/kubernetes.pem'),
        'kubernetes_key_pem': get_cert('ca/kubernetes-key.pem'),
    }

    instances = {
        'resources/controller.yaml': [
            {
                'name': 'controller{0}'.format(num),
                'privateip': '10.240.0.{0}'.format(10 + num),
                'userdata_template': 'controller-cloud-init.yaml',
                **certs,
            }
            for num in range(CONTROLLER_INSTANCES)
        ],
        'resources/worker.yaml': [
            {
                'name': 'worker{0}'.format(num),
                'privateip': '10.240.0.{0}'.format(20 + num),
                'userdata_template': 'worker-cloud-init.yaml',
                **certs,
            }
            for num in range(WORKER_INSTANCES)
        ],
    }

    # combine files into final template
    resources = {}
    for template_filename in resource_templates:
        with open(template_filename) as template_file:
            template = yaml.load(template_file)
            for key, value in template.items():
                resources[key] = value
    for template_filename in instances:
        for format_params in instances[template_filename]:
            with open(template_filename) as template_file:
                userdata = get_userdata(**format_params)
                template = yaml.load(template_file.read().format(
                    **format_params,
                    userdata=userdata))
                for key, value in template.items():
                    resources[key] = value

    parameters = yaml.load(open('parameters.yaml'))
    vpc_template = {
        'Description': 'private VPC for kubernetes cluster',
        'Parameters': parameters,
        'Resources': resources,
    }

    # now create the stack using our template
    data = yaml.dump(vpc_template, default_flow_style=False)
    s3.upload(data, 'kubernetes-on-aws.yaml')


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

    build_template()
    stack = cf_func(
        StackName=stackname,
        TemplateURL='https://s3-us-west-2.amazonaws.com/kubernetes-on-aws/kubernetes-on-aws.yaml',
        Parameters=[
            {'ParameterKey': 'InstanceKeyPair', 'ParameterValue': 'paul.sevcik'},
            {'ParameterKey': 'MyIP', 'ParameterValue': getmyip()},
        ]
    )

    # wait for all AWS objects to get applied
    stackid = stack['StackId']
    waiter = cloudformation.get_waiter(cf_waiter)
    waiter.wait(StackName=stackid)


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

    s3.delete_bucket()

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

    commands = ['create', 'delete', 'update', 'names']
    parser = argparse.ArgumentParser()
    parser.add_argument('cmd', help='command to run, one of %s' % ' '.join(commands))
    args = parser.parse_args()

    if args.cmd not in commands:
        import sys
        parser.print_help()
        sys.exit(1)

    command_func = locals()[args.cmd]
    command_func(boto3.client('cloudformation'), 'Kubernetes-in-AWS')
