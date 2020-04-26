account = "nonprod"

environment = "dev"

cidr_block = "10.1.0.0/16"

# This directory has a custom workflow file which overrides the root module
# with a newer version that introduces the `tags_for_resource` variable:

tags_for_resource = {
  aws_vpc = {
    NewerRootModule = "true"
  }
}
