#!/usr/bin/env python3
"""CDK app entry point for VPC Foundation infrastructure."""

import aws_cdk as cdk
from stack import VpcStack

app = cdk.App()

# Configuration from CDK context (set by GitHub Actions) or scaffolder defaults
component_name = app.node.try_get_context("component_name") or "${{ values.name }}"
environment = app.node.try_get_context("environment") or "${{ values.environment }}"
vpc_cidr = app.node.try_get_context("vpc_cidr") or "${{ values.vpcCidr }}"
availability_zones = int(app.node.try_get_context("availability_zones") or "${{ values.availabilityZones }}")
enable_nat_gateway = str(app.node.try_get_context("enable_nat_gateway") or "${{ values.enableNatGateway }}").lower() == "true"
single_nat_gateway = str(app.node.try_get_context("single_nat_gateway") or "${{ values.singleNatGateway }}").lower() == "true"
enable_vpc_endpoints = str(app.node.try_get_context("enable_vpc_endpoints") or "${{ values.enableVpcEndpoints }}").lower() == "true"

VpcStack(
    app,
    f"{component_name}-{environment}-stack",
    component_name=component_name,
    environment=environment,
    vpc_cidr=vpc_cidr,
    availability_zones=availability_zones,
    enable_nat_gateway=enable_nat_gateway,
    single_nat_gateway=single_nat_gateway,
    enable_vpc_endpoints=enable_vpc_endpoints,
    env=cdk.Environment(
        account=app.node.try_get_context("aws_account_id") or "${{ values.accountId }}",
        region=app.node.try_get_context("aws_region") or "${{ values.awsRegion }}",
    ),
    tags={
        "environment": environment,
        "owner": "${{ values.owner }}",
        "genforge:managed": "true",
    },
)

app.synth()
