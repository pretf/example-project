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
  * Enforces better coding practices - feature flags and versioned remote root modules.
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

## Hierachy and detecting changes in a CI/CD system

The hierarchy of this example project is crucial.

Consider this non-hierarchical project structure:

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

The hierarchy of this project makes it easy to determine which directories to plan/apply whenever files have changed. If you edit `vpc/main.tf` then it will potentially affect all directories below it: `vpc/dev` and `vpc/prod`. If you edit `vpc/dev/terraform.tfvars` then it will only affect itself, as it is at the bottom of the hierarchy.

But where did the `tags` module go?

Let's say that the module was only used by the `vpc` directory and it was very simple. In this case, we'd just move it into `vpc/tags.tf`. Just like `vpc/main.tf`, changes to `vpc/tags.tf` will potentially affect the directories below it: `vpc/dev` and `vpc/prod`.

Let's say that the module was used by both `vpc` and `vpc-peering` stacks. In this case, we'd move it into a separate git repository, and `vpc/main.tf` and `vpc-peering/main.tf` would include it as a versioned remote module. When changes are made to the `tags` module repository, and a new version is released, we would update `vpc/main.tf` and `vpc-peering/main.tf` to use the new version. We can now determine that all directories below `vpc` and `vpc-peering` have potentially changed, but the `iam` directory has not.

## Hierarchy, CI/CD, and making changes to specific environments

This hierarchical project structure supports and encourages having a project where **everything** in the master branch has been deployed to production. There should never be a situation where you have code in the master branch that has been applied to dev but you're waiting to test it before applying it to production. Untested changes from one pull request should not block another pull request.

So how does it work? Let's use the same structure from last time:

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

If you make a change to `vpc/main.tf`, it might affect `vpc/dev` and `vpc/prod`. If your CI/CD system plans and applies changes to both stacks at the same time, then this will practically force you into making changes that only affect one of them at a time.

There are 3 main ways to do this.

You can start by putting conditional logic directly in your Terraform code. Actually, don't do this, it is messy.

```hcl
resource "aws_s3_bucket" "this" {
  count  = var.env == "dev" || var.env == "stage" ? 1 : 0  # enabled with conditional logic
  bucket = "my-bucket-${var.env}"
  acl    = "private"

  dynamic "versioning" {
    for_each = var.env == "dev" ? [1] : []                 # enabled with conditional logic
    content {
      enabled = true
    }
  }
}
```

A better way is to add feature flag variables. Define the feature flag variables and enable or disable them in your `.tfvars` files.

```hcl
variable "enable_bucket" {
  default = false
}

variable "enable_bucket_versioning" {
  default = false
}

resource "aws_s3_bucket" "this" {
  count  = var.enable_bucket ? 1 : 0                            # enabled in tfvars
  bucket = "my-bucket-${var.env}"
  acl    = "private"

  dynamic "versioning" {
    for_each = var.enable_bucket_versioning != null ? [1] : []  # enabled in tfvars
    content {
      enabled = true
    }
  }
}
```

Another way is to use versioned remote modules.

```hcl
variable "enable_bucket" {
  default = false
}

# in dev:

module "bucket" {
  source  = "fake-modules/s3-bucket/aws"
  version = "1.1.0"                      # this module version introduced and enabled bucket versioning
  name    = "my-bucket-${var.env}"
  enabled = var.enable_bucket            # enabled in tfvars
}

# in stage:

module "bucket" {
  source  = "fake-modules/s3-bucket/aws"
  version = "1.0.0"                      # this module version did not have bucket versioning
  name    = "my-bucket-${var.env}"
  enabled = var.enable_bucket            # enabled in tfvars
}

# in prod:

module "bucket" {
  source  = "fake-modules/s3-bucket/aws"
  version = "1.0.0"                      # this module version did not have bucket versioning
  name    = "my-bucket-${var.env}"
  enabled = var.enable_bucket            # disabled in tfvars
}
```

If you want to version an entire stack with different environments using different versions of code, Pretf can help. See the [vpc](vpc) stack for an example of this.

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
