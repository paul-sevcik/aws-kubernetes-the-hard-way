"""
Use Cloudformation to create all VPC elements, including InternetGateway,
RouteTable, and Subnet.
"""
import argparse

import boto3
import yaml


def build_template():

    # break the template into separate files to make it easier to understand
    template_files = [
        'resources/vpc.yaml',
        'resources/internet-gateway.yaml',
        'resources/route-table.yaml',
        'resources/subnet.yaml',

        'resources/security.yaml',
        'resources/etcd.yaml',
    ]

    # combine files into final template
    resources = {}
    for template_filename in template_files:
        with open(template_filename) as template_file:
            template = yaml.load(template_file)
            for key, value in template.items():
                resources[key] = value
    parameters = yaml.load(open('parameters.yaml'))
    vpc_template = {
        'Description': 'private VPC for kubernetes cluster',
        'Parameters': parameters,
        'Resources': resources,
    }

    # now create the stack using our template
    return yaml.dump(vpc_template, default_flow_style=False)


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

    vpc_yaml = build_template()
    stack = cf_func(
        StackName=stackname,
        TemplateBody=vpc_yaml,
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
    print('creating the stack')
    apply_template(cloudformation, stackname, create_stack=False)
    print('stack update complete')


def delete(cloudformation, stackname):
    print('deleting the stack')
    cloudformation.delete_stack(StackName=stackname)

    waiter = cloudformation.get_waiter('stack_delete_complete')
    waiter.wait(StackName=stackname)
    print('stack deletion complete')


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('cmd', help='command to run, either create or delete')
    args = parser.parse_args()

    if args.cmd not in ['create', 'delete']:
        import sys
        parser.print_help()
        sys.exit(1)

    command_func = {
        'create': create,
        'delete': delete,
    }
    command_func[args.cmd](boto3.client('cloudformation'), 'Kubernetes-in-AWS')
