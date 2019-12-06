from hashlib import sha256
import math 
from multiprocessing import Pool
from itertools import product
import sys
import time

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

def findNonceAssist(lst):
    D, block, i = lst
    for i in xrange(i[0], i[1]):
        left = 0
        remaining = D
        newBlock = block + str(i)
        signature = sha256(sha256(newBlock.encode()).digest()).hexdigest()

        while signature[left] == '0':
            remaining = remaining - 4
            left += 1
            if remaining < 1:
                return i 
        
        if remaining < 4:
            binaryMatch = hex2bin_map[signature[left]]
            if("1" not in binaryMatch[0:remaining]):
                return i
    return -1

if __name__ == '__main__':
    goFrom = 0
    goTo = 2**32-1
    n_processes = 8
    D = 10
    startTime = time.time()

    if len(sys.argv) > 1:
        D = int(sys.argv[1])

    if len(sys.argv) > 2:
        n_processes = int(sys.argv[2])

    if len(sys.argv) > 4:
        goFrom = int(sys.argv[3])
        goTo = int(sys.argv[4])

    batch_size = int(2.5e5)
    pool = Pool(n_processes)
    nonce = goFrom
    while True:
        roundCap = min(nonce + (n_processes * batch_size), goTo - goFrom)
        sizePerProcess = int(math.ceil(roundCap / n_processes))
        nonce_ranges = [(nonce + i * sizePerProcess, nonce + (i+1) * sizePerProcess)for i in range(n_processes)]
        params = [
            (D, "COMSM0010cloud", nonce_range) for nonce_range in nonce_ranges
        ]
        solutions = pool.map(findNonceAssist, params)
        solutions = filter(lambda x: x != -1, solutions)
        t = list(solutions)
        nonce += n_processes * batch_size
        if(len(t) > 0):
            print(t[0], time.time() - startTime) #single golden nonce, others are omitted for now
            break
        elif nonce > goTo:
            print(-1, time.time() - startTime)
            break

