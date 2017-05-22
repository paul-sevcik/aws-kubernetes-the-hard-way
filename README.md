My version of Kelsey Hightower's Kubernetes the Hard Way (https://github.com/kelseyhightower/kubernetes-the-hard-way).
The infrastucture is built in AWS using python/boto3 and CloudFoundation instead of Google Cloud Platform.  To create
the cluster, create a virtual environment, install the packages in requirements.txt, then run 'python3 vpc.py create'.

AMI's
-----
Build AMI's for the controller and worker instances using Packer.