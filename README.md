# Pretf Example Project

Short version:

* Managed DRY S3 Terraform backend.
  * Use variables when defining backend.
  * Create S3 bucket and DynamoDB table using CloudFormation.
* Multiple AWS profiles with MFA in single stack.
  * Good for VPC peering, DNS delegation, and other cross-account systems.
* Run locally with pure Terraform commands and no extra CLI arguments.
* Run in simple CI/CD system with pull requests for code review and plan approval.
* Ensure code matches reality by applying changes to all environments immediately.
  * Encourages better development practices, using feature flags and versioned remote root modules.
* Ability to generate complex configuration with Python when HCL is too limited.

This example project demonstrates:

* Multiple stacks with multiple environments.
    * E.g. deploy the same VPC stack to dev, stage and prod environments with different variables.
* Directory based Terraform commands with no arguments required.
    * E.g. `cd stacks/vpc/dev && terraform plan`
* Remote backend management.
    * The backend is defined once and uses variables to avoid repetition.
    * The user is prompted to create the backend resources (S3 bucket and DynamoDB table) if they don't exist. These resources are created using CloudFormation.
    * Terraform Workspaces require all environments to use the same backend; that is not the case here; each AWS account has its own S3 bucket and DynamoDB table.
* Root modules in same repository.
    * No version pinning, so changes to modules affect all environments using them.
    * Use of feature flags and keeping forward/backward compatibility is recommended.
    * Faster development cycle, less controlled release process.
    * Start here and easily convert to versioned root module later.
* Versioned root modules from a remote source.
    * E.g. downloads the VPC module from the Terraform registry.
    * Has version pinning, so changes can be applied to environments individually.
    * Slower development cycle, more controlled release process.
* Using outputs from one stack as inputs for another.
    * No need for `terraform_remote_state` data sources which require full read access to the state file.

Many of the features and goals of this example, and Pretf itself, are inspired and influenced by [Terragrunt](https://terragrunt.gruntwork.io/). They have some good ideas. Some reasons to choose Pretf are:

* Pretf has better support for AWS credentials.
    * Supports multiple AWS providers in the same stack, using multiple MFA-protected profiles. This results in much simpler Terraform code when dealing with cross-account VPC peering, cross-account Route 53 zone delegation, etc.
* Pretf lets you generate complex Terraform configuration with Python code.
    * This is completely optional, many projects do not need this.
* Pretf lets you configure everything with Python code.
    * This is completely optional, but recommended.
    * This example demonstrates just one way to augment a Terraform project. You can write your own `pretf.workflow.py` file(s) and do anything you want.

## Detecting changes in a CI/CD system

When submitting a pull request, the CI/CD system detects which stacks have changed and automatically runs `terraform plan` where appropriate. This section explains how this works.

Consider this project structure:

```
modules/
    tags/
        main.tf
params/
    iam/
        dev.tfvars
        prod.tfvars
    vpc/
        dev.tfvars
        prod.tfvars
    vpc-peering/
        dev.tfvars
        prod.tfvars
stacks/
    iam/
        main.tf
    vpc/
        main.tf
    vpc-peering/
        main.tf
```

It is not clear which stacks use `modules/tags`. There is no easy way to determine which stacks will be affected when changes have been made to `modules/tags/main.tf`.

> Note: [terraform-diff](https://github.com/contentful-labs/terraform-diff) and similar approaches could help with some cases, but it would need to be aware of (or make assumptions about) the structure of the project. Pretf supports custom workflows to allow many different project structures. Supporting something so flexible would probably be difficult or messy.

Now consider this *hierarchical* project structure:

```
iam/
    main.tf
    dev/
        terraform.tfvars
    prod/
        terraform.tfvars
vpc/
    main.tf
    dev/
        terraform.tfvars
    prod/
        terraform.tfvars
vpc-peering/
    main.tf
    dev/
        terraform.tfvars
    prod/
        terraform.tfvars
```

The hierarchy of this project makes it easy to determine which directories to plan/apply when files have changed. If you edit `vpc/main.tf` then it will potentially affect all directories below it: `vpc/dev` and `vpc/prod`. If you edit `vpc/dev/terraform.tfvars` then it will only affect itself, as it is at the bottom of the hierarchy.

But where did the `tags` module from the first structure go?

Let's say that the module was only used by the `vpc` directory and it was very simple. In this case, we'd just move it into `vpc/tags.tf`. Just like `vpc/main.tf`, changes to `vpc/tags.tf` will potentially affect the directories below it: `vpc/dev` and `vpc/prod`.

Let's say that the module was used by both `vpc` and `vpc-peering` stacks. In this case, we'd move it into a separate git repository, and `vpc/main.tf` and `vpc-peering/main.tf` would include it as a versioned remote module. When changes are made to the `tags` module repository, and a new version is released, we would update `vpc/main.tf` and `vpc-peering/main.tf` to use the new version. We can now determine that all directories below `vpc` and `vpc-peering` have potentially changed, but the `iam` directory has not.

## Making changes to specific environments

When submitting a pull request, the CI/CD system will plan all affected stacks as a group, and apply all affected stacks as a group. This encourages having **everything** in the master branch deployed immediately, which in turn discourages you from making changes that affect multiple environments.

If a CI/CD system has multiple deployment stages (for example: deploy to dev, wait for approval, deploy to stage, wait for approval, deploy to prod) then *the intended state of the infrastructure is hidden within the current state of the CI/CD system*.

Applying all changes immediately encourages better development practices, using feature flags and versioned remote root modules.

How does it work? Let's use the same structure from last time:

```
iam/
    main.tf
    dev/
        terraform.tfvars
    prod/
        terraform.tfvars
vpc/
    main.tf
    dev/
        terraform.tfvars
    prod/
        terraform.tfvars
vpc-peering/
    main.tf
    dev/
        terraform.tfvars
    prod/
        terraform.tfvars
```

If you make a change to `vpc/main.tf`, the CI/CD system will plan and apply both `vpc/dev` and `vpc/prod` together. This practically forces you into making sure that pull requests and their changes will only affect one environment at a time.

There are 3 main ways to do this.

You can start by putting conditional logic directly in your Terraform code. Actually, don't do this, it is messy.

```hcl
resource "aws_vpc" "this" {
  cidr_block           = var.cidr_block
  enable_dns_support   = var.env == "dev" || var.env == "stage"
  enable_dns_hostnames = var.env == "dev"
}
```

A better way is to use feature flag variables. Define the feature flag variables and enable or disable them in your `.tfvars` files.

```hcl
variable "enable_dns_support" {
  default = false
}

variable "enable_dns_hostnames" {
  default = false
}

resource "aws_vpc" "this" {
  cidr_block           = var.cidr_block
  enable_dns_support   = var.enable_dns_support
  enable_dns_hostnames = var.enable_dns_hostnames
}

# in dev.tfvars

enable_dns_support = true
enable_dns_hostnames = true

# in stage.tfvars

enable_dns_support = true
```

Another way is to use versioned remote modules.

```hcl
# in dev:

module "vpc" {
  source     = "fake-modules/vpc/aws"
  version    = "1.2.0"                 # this module version sets enable_dns_support = true
  cidr_block = var.cidr_block
}

# in stage:

module "vpc" {
  source     = "fake-modules/vpc/aws"
  version    = "1.1.0"                 # this module version sets enable_dns_hostnames = true
  cidr_block = var.cidr_block
}

# in prod:

module "vpc" {
  source     = "fake-modules/vpc/aws"
  version    = "1.0.0"                 # this module version did not set any dns arguments
  cidr_block = var.cidr_block
}
```

Pretf has 2 features that help use different module versions in different environments:

1. Generate the configuration with Python. This allows you to use a variable in the module version argument.
2. Use [workflow.link_module()](https://pretf.readthedocs.io/en/latest/api/workflow/#link_module) in a custom workflow to use a versioned remote module as a root module. See the [vpc](vpc) stack for an example of this.

## Thoughts on drift detection

There are multiple ways for the infrastructure and code to "drift" apart.

1. An external process (such as a user in the AWS console) changes the infrastructure.
2. Changes have been made to one stack which affects another stack.

We cannot reasonably fully prevent the first scenario from happening, so we want some form of drift detection for all stacks/environments in the project. This would need to run on a regular schedule (e.g. every hour) because we don't know when changes might happen.

The second scenario is likely to happen in many projects. Ideally, the system would automatically detect which dependant stacks need updating after changes have been applied, but it is impossible to make this 100% accurate. Consider a Terraform stack that creates a CloudFormation stack that creates a Lambda function custom resource that performs a lookup on a resource created by another stack. There is no way to reliably determine that one stack relies on another stack.

We could declare relationships between stacks. This would allow a CI/CD system to quickly start the plan/approve/apply process for dependant stacks. However, this requires extra work for the project maintainers, and the only benefit this has over triggering drift detection for all stacks is that it would be faster. Unless the project has a very large number of stacks, it is probably not worth the complication of introducing the concept of stack dependencies.

Possible solution:

* Regular drift detection that creates empty pull requests if it finds unapplied changes.
* Disable drift detection while pull requests are open, enable again and run immediately after all have been closed.
    * This allows users to manually plan/apply known dedpendant stacks while the pull request is still open.
    * But this requires applying from a branch instead of master.
    * But this requires pull requests to be closed quickly. Can we make the check better than "are there any pull requests open?"
