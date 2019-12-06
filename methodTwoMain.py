import boto3
import botocore
import paramiko
import time
from threading import Thread
import sys
import math
import multiprocessing as mp
import argparse
from multiprocessing.dummy import Pool as ThreadPool
from utils import selectNumMachines, calculateRangeEnd, calculateTimeout, processCLArgs

regionCode = ''     #e.g. us-east-2
regionFullName = "" #e.g. U.S East (Ohio)

ec2 = boto3.resource('ec2', region_name=regionName)
client = boto3.client('ec2', region_name=regionName)
fullScanTime = 14095

#callback to add data to the result array
#result array is global and processed at the end
def callback(r):
    i, res = r
    result[i] = res
    if res != -1:
        pool.terminate()

#thread for handling interaction with one VM
#interaction is everything from spinning up to collecting the result
def spinSingleInstance(param):
    i, _range, difficulty = param
    _from, _to = _range
    res = client.run_instances(
        InstanceInitiatedShutdownBehavior='terminate',
        ImageId='',
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',
        KeyName="",
        SecurityGroupIds=[""]
    )
    instance_id = res['Instances'][0]['InstanceId']

    print(instance_id + " " + "spun up")
    instance = ec2.Instance(instance_id)
            
    time.sleep(60)
    result = -1
    ip = instance.public_ip_address.replace(".", "-")
    key = paramiko.RSAKey.from_private_key_file("")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname="ec2-"+ip+"."+regionName+".compute.amazonaws.com", username='ec2-user', pkey=key)
    sftp = ssh.open_sftp()
    sftp.put("methodTwoVM.py", "/home/ec2-user/golden.py")
    stdin, stdout, stderr = ssh.exec_command('python golden.py ' + str(difficulty) + " 2 " + str(_from) + " " + str(_to) + " " + instance_id)
    result = stdout.readlines()
    if len(result) > 0:
        if result[0][1:3] == "-1":
            result = -1
        else:
            result = result[0]
    else:
        result = -1
    sftp.close()
    ssh.close()
        
    return [i,result]

#wrapper for thread that also implements a timeout
def abortable_worker(in_args):
    tp = ThreadPool(1)
    timeout, tup = in_args
    res = tp.apply_async(func=spinSingleInstance, args=(tup,))
    try:
        out = res.get(timeout)  # Wait timeout seconds for func to complete.
        return out
    except Exception as e:
        tp.terminate()
        raise

#main routine for managing all threads
def applyWCallBack(timeout, numInstances, difficulty, rangeEnd):
    searchStart = 0
    searchEnd = rangeEnd

    global pool
    pool = mp.Pool(numInstances)
    global result
    result = [None] * numInstances

    gap = searchEnd - searchStart
    rangePerProcess = int(math.ceil(gap / numInstances)) + 1
    
    nonce_ranges = [[i,(i * rangePerProcess, (i+1) * rangePerProcess), difficulty]for i in range(numInstances)]
    params = [
        nonce_range for nonce_range in nonce_ranges
    ]

    for i in range(numInstances):
        pool.apply_async(func=abortable_worker, args=([timeout, params[i]], ), callback=callback)
    
    pool.close()
    pool.join()
    print(result)
    
    instances = ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    for instance in instances:
        ec2.instances.filter(InstanceIds=[instance.id]).terminate()

if __name__ == "__main__":
    args = processCLArgs()

    difficulty = args.difficulty    
    numMachines = selectNumMachines(args) #safeguard to 20 machines
    rangeEnd = calculateRangeEnd(args)
    timeout = calculateTimeout(args)
    applyWCallBack(timeout, numMachines, difficulty, rangeEnd)

