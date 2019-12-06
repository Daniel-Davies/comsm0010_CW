
# About

Welcome to my golden nonce ("number only used once") finding application.

The main purpose of the application is to demonstrate horizontal scaling on AWS. Finding a golden nonce, that is, finding whether a given number has enough zeros at its left hand side (in binary representation) is embarrassingly parallelizable, and so can be split across many machines without any need for communication. This lets you see the power that multiple disjoint machines have in delivering compute power to solve a problem.

# Pre-requisites

- The default region for this codebase is US-EAST-2 (OHIO). Change as appropriate in any resource function calls.
- Firstly, you will need to configure your Amazon Web Services CLI. See [here](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) to set up.
- Through your AWS account, generate a Key Pair for EC2 instances. This key, which you will download, should be kept safe and will be useful when setting up VMs/ using AWS services. Refer to the docs [here](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html) for more information on EC2 key pairs. This key pair will be used under the KeyPair field in the run_instances function of the queues.py file.
- You will also need to create a security group. See the Amazon docs [here](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-security-groups.html) on how to do so. This security group will be used under the SecurityGroupIDs field in the run_instances function.
- To make sure the Queue based solution works, make sure to create an IAM role that gives EC2 instances access to the SQS service. See [here](https://cloud-gc.readthedocs.io/en/latest/chapter03_advanced-tutorial/iam-role.html) for a step by step guide (the tutorial is for S3, but the process for SQS is exactly the same). When you've made the IAM role, place the title under the IamInstanceProfile field in the run_instances function.
- Queue name is currently set as "logging". This can be left if the user has no preference since creation and reading/writing all happens in the program cycle.

# Running the code

To check that you have cleared the pre-requisites before proceeding, try and simply run the queues.py file, and expect to see an output as follows:

Uploading to machine i-08d26d3ba32604518
Uploading to machine i-0f80ae5c08ce60956
Uploading to machine i-02304ff3d62c98d75
Uploading to machine i-0c354d4b48edb77aa
Done uploading
2150236108 found as golden nonce for difficulty 20 with overall computational time of 81.08
Terminating EC2 instances...
Terminating SQS resource...

### Inputting parameters

If the above example worked for you, you can now begin to play with the parameters of the program. They are as follows:

--difficulty=N => Sets the difficulty of the program to run at
--machines=N => Sets the number of machines your computation will run on
--timeout=S => In seconds, specifies a hard deadline by which the computation must finish, or resources will be terminated
--max-cost=C => In dollars, specifies the maximum cost your computation should be allowed to spend. Prices updated directly from Amazon.
--max-hourly=C => In dollars, specifies the maximum cost your computation should be allowed to spend every hour. Prices updated directly from Amazon.
--confidence=M => A percentage value. Use in conjuction with the timeout flag. Specifies how certain you want to be about finding a result.

