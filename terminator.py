import boto3
import botocore

#simple file to kill all used AWS resources

ec2 = boto3.resource('ec2', region_name='us-east-2')
client = boto3.client('ec2', region_name='us-east-2')
qcli = boto3.client('sqs', region_name="us-east-2")
sqs = boto3.resource('sqs', region_name="us-east-2")

instances = ec2.instances.filter(
    Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
for instance in instances:
    ec2.instances.filter(InstanceIds=[instance.id]).terminate()

queue = sqs.get_queue_by_name(QueueName='logging')
qcli.delete_queue(QueueUrl=queue.url)