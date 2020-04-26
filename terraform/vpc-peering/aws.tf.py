from pretf.aws import provider_aws
from pretf.blocks import data


def pretf_blocks(var):
    nonprod = yield provider_aws(
        alias="nonprod", region=var.aws_region, **var.aws_credentials["nonprod"],
    )
    yield data.aws_caller_identity.nonprod(provider=nonprod)
    yield provider_aws(
        alias="prod", region=var.aws_region, **var.aws_credentials["prod"],
    )
