import pulumi
import pulumi_aws as aws

# Create a new VPC
vpc = aws.ec2.Vpc("main-vpc", cidr_block="10.0.0.0/16", tags={"Name": "pulumi-vpc"})

# Create an Internet Gateway
internet_gateway = aws.ec2.InternetGateway("internet-gateway", vpc_id=vpc.id, tags={"Name": "pulumi-igw"})

# Create a public Route Table
public_route_table = aws.ec2.RouteTable("public-route-table", vpc_id=vpc.id, routes=[
    aws.ec2.RouteTableRouteArgs(
        cidr_block="0.0.0.0/0",
        gateway_id=internet_gateway.id
    )
], tags={"Name": "pulumi-public-rt"})

# Create a NAT Gateway
# First allocate an EIP
eip = aws.ec2.Eip("nat-gateway-eip", tags={"Name": "pulumi-eip"})

# Assuming we want the NAT Gateway in the first public subnet
public_subnet = aws.ec2.Subnet("public-subnet", vpc_id=vpc.id,
                               cidr_block="10.0.1.0/24", availability_zone="us-east-1a",
                               map_public_ip_on_launch=True, tags={"Name": "pulumi-public-subnet"})

# Associate public subnet with public route table
aws.ec2.RouteTableAssociation("public-rta",
                              route_table_id=public_route_table.id,
                              subnet_id=public_subnet.id)

nat_gateway = aws.ec2.NatGateway("nat-gateway",
                                 allocation_id=eip.id,
                                 subnet_id=public_subnet.id, tags={"Name": "pulumi-nat"})

# Create a private Route Table
private_route_table = aws.ec2.RouteTable("private-route-table", vpc_id=vpc.id, routes=[
    aws.ec2.RouteTableRouteArgs(
        cidr_block="0.0.0.0/0",
        nat_gateway_id=nat_gateway.id
    )
], tags={"Name": "pulumi-private-rt"})

# Create private subnet
private_subnet = aws.ec2.Subnet("private-subnet", vpc_id=vpc.id,
                                cidr_block="10.0.2.0/24", availability_zone="us-east-1b",
                                tags={"Name": "pulumi-private-subnet"})

# Associate private subnet with private route table
aws.ec2.RouteTableAssociation("private-rta",
                              route_table_id=private_route_table.id,
                              subnet_id=private_subnet.id)

# Create a Security Group that allows SSH traffic
ssh_security_group = aws.ec2.SecurityGroup("ssh-security-group", vpc_id=vpc.id,
                                           description="Allow SSH",
                                           ingress=[aws.ec2.SecurityGroupIngressArgs(
                                               protocol="tcp",
                                               from_port=22,
                                               to_port=22,
                                               cidr_blocks=["0.0.0.0/0"]
                                                ),
                                            aws.ec2.SecurityGroupIngressArgs(
                                               protocol="icmp",
                                               from_port=-1,
                                               to_port=-1,
                                               cidr_blocks=["0.0.0.0/0"])
                                               ],
                                            egress=[aws.ec2.SecurityGroupEgressArgs(
                                               protocol="-1",
                                               from_port=0,
                                               to_port=0,
                                               cidr_blocks=["0.0.0.0/0"]
                                           )],
                                           tags={"Name": "pulumi-sg"})

# Define your public key
public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC4nbnibM/t9FNzo3cqL663om42qFEpv0ZB/RV5KnA3Kgkbc/h+7TRQJuXkU9tyO1eO6eTf1vdQzjQGTLkvhZCDcZ7YBGkuAAgGISbl+Hx5Y0a/BmWhv1XVmiYM3/oB3jXM1Gh2EQzpK7G+FtjSROVyuaMNEMcblpyie3SD1faHZd+Cp2h2LEf7vocqtCQ1vcScfvrGcsFX+J2Jp2xUyIPHU6lYDU0TuqyJgkZ18VJwkdp7sn99yp/P/3spDrlkswtjCAT0i3UVdQqHW8ueYxIcmacc1sAVg8ppHhpiLk4ZnOcdAFStwZHBh8iXXJj4OWUBh87GUtDO8b3Y2FcD3Jsa/k8zNvExrfnGfGcUSI/COJfCpfdyHVL9OcIn42RkQFCJHrnscT9d6YkEiKjyhxV3lVYj127A9sZ9Zh2uejHwpxkE+77EOlFeqg9noD0P/wFQjFSrWM+4n5UwtopsMoolqKFyswothgZqQtLnboOOSuJ66KMEYj5X4J5c4hI0prc= dipendra@macbookpro"

# Create an EC2 Key Pair with your public key
key_pair = aws.ec2.KeyPair("test-keypair",
                           public_key=public_key,
                           tags={"Name": "test-keypair"})

# Create EC2 Instances
# Creating instances in each public and private subnet with respective network interfaces
aws.ec2.Instance("public-instance",
                 ami="ami-04b70fa74e45c3917",  # Example AMI ID
                 instance_type="t2.micro",
                 subnet_id=public_subnet.id,
                 vpc_security_group_ids=[ssh_security_group.id],
                 associate_public_ip_address=True,
                 key_name=key_pair.key_name,
                 tags={"Name": "public-instance"})

aws.ec2.Instance("private-instance",
                 ami="ami-04b70fa74e45c3917",  # Example AMI ID
                 instance_type="t2.micro",
                 subnet_id=private_subnet.id,
                 vpc_security_group_ids=[ssh_security_group.id],
                 associate_public_ip_address=False,
                 key_name=key_pair.key_name,
                 tags={"Name": "private-instance"})

# Export VPC ID and NAT Gateway Public IP
pulumi.export('vpc_id', vpc.id)
pulumi.export('nat_gateway_public_ip', eip.public_ip)