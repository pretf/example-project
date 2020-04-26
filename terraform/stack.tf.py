from pretf.aws import provider_aws, terraform_backend_s3
from pretf.blocks import variable


def pretf_blocks(var):
    # Create variables needed by this file.
    yield variable.account(type="string")
    yield variable.aws_credentials(
        default={
            "nonprod": {"profile": "pretf-nonprod"},
            "prod": {"profile": "pretf-prod"},
        }
    )
    yield variable.aws_region(default="eu-west-1")
    yield variable.environment(type="string")
    yield variable.stack(type="string")

    # Create a backend configuration using the environment details.
    # Stacks in the same account share backend resources.
    yield terraform_backend_s3(
        bucket=f"pretf-example-project-{var.account}",
        dynamodb_table=f"pretf-example-project-{var.account}",
        key=f"{var.stack}/{var.environment}/terraform.tfstate",
        region=var.aws_region,
        **var.aws_credentials[var.account],
    )

    # Create a default AWS provider for this environment.
    yield provider_aws(
        region=var.aws_region, **var.aws_credentials[var.account],
    )
