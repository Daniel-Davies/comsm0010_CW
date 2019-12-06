from hashlib import sha256
import math 
from multiprocessing import Pool
import sys
import time
import boto3 
import json 

regionName = ""  #e.g. us-east-2

#hash table for checking final char comparisons
hex2bin_map = {
    "0":"0000",
    "1":"0001",
    "2":"0010",
    "3":"0011",
    "4":"0100",
    "5":"0101",
    "6":"0110",    
    "7":"0111",
    "8":"1000",
    "9":"1001",
    "a":"1010",
    "b":"1011",
    "c":"1100",
    "d":"1101",
    "e":"1110",
    "f":"1111",
}

#brute force method for calculating a golden nonce
def findNonceAssist(lst):
    index, D, block, indices = lst

    #loop over the given range
    for i in xrange(indices[0], indices[1]+1):
        left = 0
        remaining = D
        newBlock = block + str(bin(i))
        signature = sha256(sha256(newBlock.encode()).digest()).hexdigest()

        #each zero translated from hex = 4 bits equivalent
        while signature[left] == '0':
            remaining = remaining - 4
            left += 1
            if remaining < 1:
                return (index, i, True)
        
        #potentially still a nonce
        if remaining < 4:
            binaryMatch = hex2bin_map[signature[left]]
            if("1" not in binaryMatch[0:remaining]):
                return (index, i, True)
    return (index, -1, False)

#callback function for the findNonceAssist method-
#stores the result of a single thread in the global result array
def callback(t):
    index, res, shouldEnd = t
    result[index] = res
    if shouldEnd:
        pool.terminate()

#calculates the ranges that each thread should visit
def calculateRangesPerThread(goFrom, goTo, n_processes):
    sizePerProcess = int(math.ceil((goTo-goFrom) / n_processes))
    nonce_ranges = [(i * sizePerProcess,min((i+1) * sizePerProcess, goTo))for i in range(n_processes)]
    nonce_ranges = list(map(lambda x: (x[0]+goFrom, x[1]+goFrom), nonce_ranges))

    return nonce_ranges

#processes inbound arguments from user
def processArgs():
    goFrom = 0
    goTo = 2**32
    n_processes = 8
    D = 10
    globalMachineID = "Unknown"

    if len(sys.argv) > 1:
        D = int(sys.argv[1])

    if len(sys.argv) > 2:
        n_processes = int(sys.argv[2])

    if len(sys.argv) > 4:
        goFrom = int(sys.argv[3])
        goTo = int(sys.argv[4])
    
    if len(sys.argv) > 5:
        globalMachineID = sys.argv[5]
    
    return goFrom, goTo, D, globalMachineID, n_processes

#find reference to the main SQS queue
def getQueueInstance():
    sqs = boto3.resource('sqs', region_name=regionName)
    return sqs.get_queue_by_name(QueueName='logging')

#send a result to the SQS for further communication
def processResult(result, globalMachineID):
    result = list(filter(lambda x: x != -1 and x is not None, result))
    toSave = ""
    if(len(result) > 0):
        toSave = {"result": "Success", "value": result[0] , "timing": "{0:.2f}".format(time.time() - startTime), "type":"result", "id": globalMachineID }
    else:
        toSave = {"result": "Failed", "value": -1 , "timing": "{0:.2f}".format(time.time() - startTime), "type":"result", "id": globalMachineID}
    
    queue.send_message(MessageBody=json.dumps(toSave))


#main controlling method
if __name__ == "__main__":
    queue = getQueueInstance()
    startTime = time.time()
    goFrom, goTo, D, globalMachineID, n_processes = processArgs()
    nonce_ranges = calculateRangesPerThread(goFrom, goTo, n_processes)
    beginExecLog = {"result": "Machine " + globalMachineID + " has begun to execute", "timing":  "{0:.2f}".format(time.time()), "type":"log" }
    queue.send_message(MessageBody=json.dumps(beginExecLog))

    result = [None] * n_processes
    pool = Pool()

    for i in range(n_processes):
        pool.apply_async(func=findNonceAssist, args=([i, D, "COMSM0010cloud", nonce_ranges[i]], ), callback=callback)

    pool.close()
    pool.join()

    processResult(result, globalMachineID)