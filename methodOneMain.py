import boto3
import botocore
import paramiko
import time
import sys
import math
import multiprocessing as mp
import argparse
from multiprocessing.dummy import Pool as ThreadPool
import json
from datetime import datetime
from costAPI import getPrice
from utils import selectNumMachines, calculateRangeEnd, calculateTimeout, processCLArgs

#constant variables used for user calculations and resources
fullScanTime = 14095 #in seconds

regionCode = ''     #e.g. us-east-2
regionFullName = "" #e.g. U.S East (Ohio)

#main boto objects for interacting with resources
ec2 = boto3.resource('ec2', region_name=regionCode)
client = boto3.client('ec2', region_name=regionCode)
sqs = boto3.resource('sqs', region_name=regionCode)
qcli = boto3.client('sqs', region_name=regionCode)


#return objects corresponding to N EC2 instances and new queue 
def fireUpResources(numInstances):
    res = client.run_instances(
        InstanceInitiatedShutdownBehavior='terminate',
        ImageId='',         #e.g. ami-XXXXXXXXXXXX
        MinCount=1,
        MaxCount=numInstances,
        InstanceType='t2.micro',
        KeyName="",
        IamInstanceProfile={'Name': ''},
        SecurityGroupIds=[""],
        UserData="""#!/bin/bash
                    sudo yum install -y python-pip
                    sudo pip install boto3 
                """
        )

    queue = sqs.create_queue(QueueName='logging')
    return res["Instances"], queue 

#calculate the load for each machine
def getRangesPerMachine(rangeEnd, numInstances):
    searchStart = 0
    searchEnd = rangeEnd
    gap = searchEnd - searchStart
    rangePerProcess = int(math.ceil(gap / numInstances)) + 1
    nonce_ranges = [(i * rangePerProcess, (i+1) * rangePerProcess)for i in range(numInstances)]

    return nonce_ranges

#safely clean up resources when finished using AWS commands
def terminateResources(queue):
    print("Terminating EC2 instances...")
    instances = ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    for instance in instances:
        ec2.instances.filter(InstanceIds=[instance.id]).terminate()
    print("Terminating SQS resource...")
    qcli.delete_queue(QueueUrl=queue.url)

#main parallel method used for receving updates from seperate machines
def queueHandler(queue, numInstances, timeout, startTime):
    timeoutLimit = startTime + timeout

    awaitingResult = True
    logs = []
    heardFrom = 0
    while awaitingResult:
        #get all messages sent by machines
        for message in queue.receive_messages():
            payload = json.loads(message.body)
            #json packet comes back with result
            if payload["type"] == "result" and payload["result"] == "Success":
                awaitingResult = False
                print(str(payload["value"]) + " found as golden nonce for difficulty " + str(difficulty) + " with overall computational time of " + "{0:.2f}".format(time.time() - startTime))
                print("local exec time was " + str(payload["timing"]))
                break
            #machine has searches range and not found a result
            elif payload["type"] == "result" and payload["result"] == "Failed":
                heardFrom += 1
                if heardFrom == numMachines:
                    awaitingResult = False
                    print("No Golden Nonce found for difficulty " + str(difficulty))
                instance = ec2.Instance(payload["id"]).terminate()
            #logging information from the machine
            elif payload["type"] == "log":
                logs.append({"Message": payload["result"], "RelTime": datetime.now().strftime("%m/%d/%Y, %H:%M:%S")} )
            message.delete()
        #user specified timout limit reaches
        if time.time() > timeoutLimit:
            awaitingResult = False
            #write data to log file
            f = open('logs.txt', 'w')
            f.write(str(logs))
            f.close()
            print("Operation timed out to user specification. See logs for work completed up to limit.")    

# concurrent method for SFTPing data to a VM
def uploadToMachines(args):
    i, nonce_ranges, inst, difficulty = args
    instance_id = inst['InstanceId']
    instance = ec2.Instance(instance_id)
    instance.wait_until_running()
    indivStartTime = time.time()
    time.sleep(60) #wait 60 seconds for SSH ports to open
    print("Uploading to machine " + instance_id)
    ip = instance.public_ip_address.replace(".", "-")
    key = paramiko.RSAKey.from_private_key_file("")   #e.g. .pem file from AWS
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname="ec2-"+ip+"."+regionCode+".compute.amazonaws.com", username='ec2-user', pkey=key)
    sftp = ssh.open_sftp()
    _from, _to = nonce_ranges
    sftp.put("methodOneVM.py", "/home/ec2-user/golden.py")
    ssh.exec_command('python golden.py ' + str(difficulty) + " 2 " + str(_from) + " " + str(_to) + " " + instance_id)
    sftp.close()
    ssh.close()
    return (i, indivStartTime)

def callback(args):
    i, timing = args
    timingResult[i] = timing


#main routine for co-ordinating the result
def applyWCallBack(timeout, numInstances, difficulty, rangeEnd):
    instances, queue = fireUpResources(numInstances)
     
    nonce_ranges = getRangesPerMachine(rangeEnd, numMachines)

    pool = mp.Pool(numInstances) #set up concurrent pool of resources

    global timingResult
    timingResult = [0] * numInstances

    for k,inst in enumerate(instances): #concurrently upload files
        pool.apply_async(func=uploadToMachines, args=([k, nonce_ranges[k], inst, difficulty], ), callback=callback)

    pool.close()
    pool.join()

    print("Done uploading")
    startTime = min(timingResult)

    queueHandler(queue, numInstances, timeout, startTime)
    terminateResources(queue)

if __name__ == "__main__":
    args = processCLArgs()

    difficulty = args.difficulty    
    timeout = calculateTimeout(args)
    numMachines = selectNumMachines(args) #safeguard to 20 machines
    rangeEnd = calculateRangeEnd(args)

    applyWCallBack(timeout, numMachines, difficulty, rangeEnd)