import argparse

regionFullName = "US East (Ohio)"

#get user specified args
def processCLArgs():
    parser = argparse.ArgumentParser(description='Make some bitcoin money')
    parser.add_argument(
        "--difficulty",
        default=20,
        type=int
    )
    parser.add_argument(
        "--machines",
        default=4,
        type=int
    )
    parser.add_argument(
        "--timeout",
        default=86400,            #make very large?
        type=int
    )
    parser.add_argument(
        "--max-cost",
        default=-1,            #make very large?
        type=float
    )

    parser.add_argument(
        "--max-hourly",
        default=-1,            #make very large?
        type=float
    )

    parser.add_argument(
        "--confidence",
        default=-1,            
        type=int
    )

    return parser.parse_args()

#method to select the number of machines given user parameters
#Priority is given lowest => highest as: 
#User specified number of machines
#confidence value specifications
#user defined constraints on cost 
def selectNumMachines(args):
    numMachines = args.machines

    if args.confidence > 0:
        if difficulty <= 20: 
            numMachines = 1
        else:
            numMachines = math.ceil((fullScanTime * 0.01 * args.confidence) / args.timeout)
    
    if args.max_hourly > 0:
        costPerHour = args.max_hourly
        pricePerHour = float(getPrice(regionFullName, 't2.micro', 'Linux')) #call price API
        exactMachines = costPerHour / pricePerHour
        numMachines = int(exactMachines)
    
    return min(numMachines, 20) #safeguard to 20

#selects the range given user parameters
#default is 2**32 unless the user specifies a confidence
def calculateRangeEnd(args):
    rangeEnd = 4294967296
    if args.confidence > 0:
        rangeEnd = int(42949672.96 * args.confidence)
    
    return rangeEnd

#calculates a timeout given user parameters
#Priority is given lowest => highest as: 
#User specified timeout 
#aximum cost constraint specified by the user
def calculateTimeout(args):
    finalTimeout = args.timeout 

    if args.max_cost > 0:
        givenCost = args.max_cost
        pricePerHour = float(getPrice(regionFullName, 't2.micro', 'Linux')) #call price API
        timeToCost = givenCost / pricePerHour
        timeToCost = timeToCost / numMachines
        finalTimeout = min(timeToCost * 3600, finalTimeout) #hours to seconds, safeguarded with finalTimeoutTime
    
    return min(finalTimeout, 86400) #safeguard to 24 hours