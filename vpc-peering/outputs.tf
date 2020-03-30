output "prod_to_stage_status" {
  value = aws_vpc_peering_connection_accepter.prod_to_stage.accept_status
}

output "stage_to_dev_status" {
  value = aws_vpc_peering_connection_accepter.stage_to_dev.accept_status
}
