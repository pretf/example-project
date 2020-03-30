# Prod -> Stage.

resource "aws_vpc_peering_connection" "prod_to_stage" {
  provider      = aws.prod
  vpc_id        = var.prod_vpc_id
  peer_owner_id = data.aws_caller_identity.nonprod.account_id
  peer_vpc_id   = var.stage_vpc_id
}

resource "aws_vpc_peering_connection_accepter" "prod_to_stage" {
  provider                  = aws.nonprod
  vpc_peering_connection_id = aws_vpc_peering_connection.prod_to_stage.id
  auto_accept               = true
}

locals {
  active_prod_vpc_peering_connection_id = aws_vpc_peering_connection_accepter.prod_to_stage.id
}

resource "aws_vpc_peering_connection_options" "prod_to_stage" {
  provider                  = aws.prod
  vpc_peering_connection_id = local.active_prod_vpc_peering_connection_id
  requester {
    allow_remote_vpc_dns_resolution = true
  }
}

resource "aws_vpc_peering_connection_options" "stage_from_prod" {
  provider                  = aws.nonprod
  vpc_peering_connection_id = local.active_prod_vpc_peering_connection_id
  accepter {
    allow_remote_vpc_dns_resolution = true
  }
}

# Stage -> Dev.

resource "aws_vpc_peering_connection" "stage_to_dev" {
  provider      = aws.nonprod
  vpc_id        = var.stage_vpc_id
  peer_owner_id = data.aws_caller_identity.nonprod.account_id
  peer_vpc_id   = var.dev_vpc_id
}

resource "aws_vpc_peering_connection_accepter" "stage_to_dev" {
  provider                  = aws.nonprod
  vpc_peering_connection_id = aws_vpc_peering_connection.stage_to_dev.id
  auto_accept               = true
}

locals {
  active_stage_vpc_peering_connection_id = aws_vpc_peering_connection_accepter.stage_to_dev.id
}

resource "aws_vpc_peering_connection_options" "stage_to_dev" {
  provider                  = aws.nonprod
  vpc_peering_connection_id = local.active_stage_vpc_peering_connection_id
  requester {
    allow_remote_vpc_dns_resolution = true
  }
}

resource "aws_vpc_peering_connection_options" "dev_from_stage" {
  provider                  = aws.nonprod
  vpc_peering_connection_id = local.active_stage_vpc_peering_connection_id
  accepter {
    allow_remote_vpc_dns_resolution = true
  }
}
