"""
Use Cloudformation to create all VPC elements, including InternetGateway,
RouteTable, and Subnet.
"""
import argparse

import boto3
import yaml

ETCD_INSTANCES = 3
CONTROLLER_INSTANCES = 3
WORKER_INSTANCES = 3


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

    instances = {
        'resources/etcd.yaml': [
            {'name': 'etcd{0}'.format(num), 'privateip': '10.43.0.{0}'.format(num+10)}
            for num in range(1, ETCD_INSTANCES+1)
        ],
        'resources/controller.yaml': [
            {'name': 'controller{0}'.format(num), 'privateip': '10.43.0.{0}'.format(num + 20)}
            for num in range(1, CONTROLLER_INSTANCES + 1)
        ],
        'resources/worker.yaml': [
            {'name': 'worker{0}'.format(num), 'privateip': '10.43.0.{0}'.format(num + 30)}
            for num in range(1, WORKER_INSTANCES + 1)
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
                template = yaml.load(template_file.read().format(**format_params))
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
    print('updating the stack')
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

    if args.cmd not in ['create', 'delete', 'update']:
        import sys
        parser.print_help()
        sys.exit(1)

    command_func = locals()[args.cmd]
    command_func(boto3.client('cloudformation'), 'Kubernetes-in-AWS')
