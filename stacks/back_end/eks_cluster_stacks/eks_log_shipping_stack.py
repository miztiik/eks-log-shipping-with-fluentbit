from aws_cdk import aws_eks as _eks
from aws_cdk import aws_sqs as _sqs
from aws_cdk import aws_iam as _iam
from aws_cdk import core as cdk

from stacks.miztiik_global_args import GlobalArgs


class EksLogShippingStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        construct_id: str,
        stack_log_level: str,
        eks_cluster,
        clust_oidc_provider_arn,
        clust_oidc_issuer,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Add your stack resources below):

        ###############################################
        #######                                 #######
        #######   Cloudwatch Agent Namespace    #######
        #######                                 #######
        ###############################################

        app_grp_01_name = "amazon-cloudwatch"
        app_grp_01_ns_name = f"{app_grp_01_name}"
        app_grp_01_label = {"app": f"{app_grp_01_name}"}

        app_grp_01_ns_manifest = {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {
                "name": f"{app_grp_01_ns_name}",
                        "labels": {
                            "name": f"{app_grp_01_ns_name}"
                        }
            }
        }

        # Create the App 01 (Producer Namespace)
        app_grp_01_ns = _eks.KubernetesManifest(
            self,
            f"{app_grp_01_name}-ns",
            cluster=eks_cluster,
            manifest=[
                app_grp_01_ns_manifest
            ]
        )

        #######################################
        #######                         #######
        #######   K8s Service Account   #######
        #######                         #######
        #######################################

        svc_accnt_name = "fluent-bit"
        svc_accnt_ns = app_grp_01_ns_name

        # To make resolution of LHS during runtime, pre built the string.
        oidc_issuer_condition_str = cdk.CfnJson(
            self,
            "oidc-issuer-str",
            value={
                f"{clust_oidc_issuer}:sub": f"system:serviceaccount:{svc_accnt_ns}:{svc_accnt_name}"
            },
        )

        # Svc Account Role
        self._log_shipper_role = _iam.Role(
            self,
            "fluentbit-log-shipper-svc-accnt-role",
            assumed_by=_iam.FederatedPrincipal(
                federated=f"{clust_oidc_provider_arn}",
                conditions={
                    "StringEquals": oidc_issuer_condition_str
                },
                assume_role_action="sts:AssumeRoleWithWebIdentity"
            ),
            # managed_policies=[
            #     _iam.ManagedPolicy.from_aws_managed_policy_name(
            #         "AmazonSQSFullAccess"
            #     )
            # ]
        )

        # Allow CW Agent to create Logs
        self._log_shipper_role.add_to_policy(
            _iam.PolicyStatement
            (
                actions=[
                    "logs:CreateLogStream",
                    "logs:CreateLogGroup",
                    "logs:DescribeLogStreams",
                    "logs:PutLogEvents"
                ],
                resources=["*"]
            )
        )

        _log_shipper_svc_accnt_manifest = {
            "apiVersion": "v1",
            "kind": "ServiceAccount",
            "metadata": {
                "name": f"{svc_accnt_name}",
                "namespace": f"{svc_accnt_ns}",
                "annotations": {
                    "eks.amazonaws.com/role-arn": f"{self._log_shipper_role.role_arn}"
                }
            }
        }

        _log_shipper_svc_accnt = _eks.KubernetesManifest(
            self,
            f"{svc_accnt_name}",
            cluster=eks_cluster,
            manifest=[
                _log_shipper_svc_accnt_manifest
            ]
        )

        # Create config map that can be used by FluentBit DaemonSet

        _log_shipper_config_map_manifest = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": "fluent-bit-cluster-info",
                "namespace": f"{app_grp_01_ns_name}"},
            "data":
                {
                    "cluster.name": f"{eks_cluster.cluster_name}",
                    "http.port": "2020",
                    "http.server": "On",
                    "logs.region": f"{cdk.Aws.REGION}",
                    "read.head": "Off",
                    "read.tail": "On",
                    "miztiik.automation": "True"
            }

        }

        _log_shipper_config_map = _eks.KubernetesManifest(
            self,
            "logShipperConfigMap",
            cluster=eks_cluster,
            manifest=[
                _log_shipper_config_map_manifest
            ]
        )

        ###########################################
        ################# OUTPUTS #################
        ###########################################
        output_0 = cdk.CfnOutput(
            self,
            "AutomationFrom",
            value=f"{GlobalArgs.SOURCE_INFO}",
            description="To know more about this automation stack, check out our github page.",
        )

        output_1 = cdk.CfnOutput(
            self,
            "ExternalDnsProviderRole",
            value=f"{self._log_shipper_role.role_arn}",
            description="External DNS Provider Role"
        )
