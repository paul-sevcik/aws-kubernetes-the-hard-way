
from datetime import datetime

import boto3
import botocore.exceptions

s3 = boto3.resource('s3')
bucket = s3.Bucket('kubernetes-on-aws')


def make_bucket():
    """
    Make sure the bucket has been created.
    """

    # Check if bucket already exists.
    try:
        # If the bucket doesn't exist, then looking up the date will raise an exception.
        if not isinstance(bucket.creation_date, datetime):
            raise RuntimeError('Invalid creation date on S3 bucket')
        # If no exception was raised, then it must exist already.
        need_to_create = False
    except botocore.exceptions.ClientError:
        need_to_create = True

    if need_to_create:
        bucket.create(
            ACL='private',
            CreateBucketConfiguration={'LocationConstraint': 'us-west-2'},
        )

    assert isinstance(bucket.creation_date, datetime)


def delete_bucket():
    bucket.objects.delete()
    bucket.delete()


def upload(content, filename):
    make_bucket()

    bucket.put_object(Body=content, Key=filename)

    # TODO: verify upload


if __name__ == '__main__':
    make_bucket()
