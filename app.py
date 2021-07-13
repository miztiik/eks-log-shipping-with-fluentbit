#!/usr/bin/env python3
import os
from aws_cdk import core as cdk

from stacks.back_end.vpc_stack import VpcStack
from stacks.back_end.eks_cluster_stacks.eks_cluster_stack import EksClusterStack
from stacks.back_end.eks_cluster_stacks.eks_ssm_daemonset_stack.eks_ssm_daemonset_stack import EksSsmDaemonSetStack
from stacks.back_end.eks_cluster_stacks.eks_log_shipping_stack import EksLogShippingStack


app = cdk.App()

stack_uniqueness=f"-01"

# VPC Stack for hosting Secure workloads & Other resources
vpc_stack = VpcStack(
    app,
    # f"{app.node.try_get_context('project')}-vpc-stack",
    f"eks-cluster-vpc-stack{stack_uniqueness}",
    stack_log_level="INFO",
    description="Miztiik Automation: Custom Multi-AZ VPC"
)


# EKS Cluster to process event processor
eks_cluster_stack = EksClusterStack(
    app,
    f"eks-cluster-stack{stack_uniqueness}",
    stack_log_level="INFO",
    vpc=vpc_stack.vpc,
    description="Miztiik Automation: EKS Cluster to process event processor"
)

# Bootstrap EKS Nodes with SSM Agents
ssm_agent_installer_daemonset = EksSsmDaemonSetStack(
    app,
    f"ssm-agent-installer-daemonset-stack{stack_uniqueness}",
    stack_log_level="INFO",
    eks_cluster=eks_cluster_stack.eks_cluster_1,
    description="Miztiik Automation: Bootstrap EKS Nodes with SSM Agents"
)

# Setting up CloudWatch Service Account and Namespace for Services on AWS
eks_log_shipping_stack = EksLogShippingStack(
    app,
    f"eks-log-shipping-stack{stack_uniqueness}",
    stack_log_level="INFO",
    eks_cluster=eks_cluster_stack.eks_cluster_1,
    clust_oidc_provider_arn=eks_cluster_stack.clust_oidc_provider_arn,
    clust_oidc_issuer=eks_cluster_stack.clust_oidc_issuer,
    description="Miztiik Automation: Setting up CloudWatch Service Account and Namespace for Services on AWS"
)

# Stack Level Tagging
_tags_lst = app.node.try_get_context("tags")

if _tags_lst:
    for _t in _tags_lst:
        for k, v in _t.items():
            cdk.Tags.of(app).add(
                k, v, apply_to_launched_instances=True, priority=300)

app.synth()
