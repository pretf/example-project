# Pretf Example Project

Desired features and qualities:

* Multiple AWS profiles with MFA in single stack.
  * Good for VPC peering, DNS delegation, and other cross-account systems.
* Managed DRY S3 Terraform backend.
  * Allow use of variables when defining backend.
  * Automatically create S3 backend resources.
* Run locally with pure Terraform commands and no extra CLI arguments.
* Run in GitHub Actions as part of pull requests.
  * Review and approve plans before applying changes.
* Ensure code matches reality by applying all changes together.
  * Encourages better development practices, using feature flags and versioned remote root modules.
  * No more "don't run Terraform in production, we haven't finished testing it in the development environment yet".
* Ability to generate configuration with Python to work around Terraform/HCL limitations.
    * Dynamic backend configuration.
    * Dynamic module source and version.
    * Complicated resources.

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

If you don't have a CI/CD system and you're manually applying a Terraform change across multiple environments and testing each one as you go, then *the intended state of the infrastructure is hidden within your head*.

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

1. Generate the configuration with Python. This allows you to use a variable in the module version argument, which can be set to different values per environment.
2. Use [workflow.link_module()](https://pretf.readthedocs.io/en/latest/api/workflow/#link_module) in a custom workflow to use a versioned remote module as a root module. See the [vpc](vpc) stack for an example of this.

## Thoughts on drift detection

There are multiple ways for the infrastructure and code to "drift" apart.

1. An external process (such as a user in the AWS console) changes the infrastructure.
2. Changes have been made to one stack which affects another stack.

We cannot reasonably fully prevent the first scenario from happening, so we want some form of drift detection for all stacks/environments in the project. This would need to run on a regular schedule (e.g. every hour) because we don't know when changes might happen.

The second scenario is likely to happen in many projects. Ideally, the system would automatically detect which dependant stacks need updating after changes have been applied, but it is impossible to make this 100% accurate. Consider a Terraform stack that creates a CloudFormation stack that creates a Lambda function custom resource that performs a lookup on a resource created by another stack. There is no way to reliably determine that one stack relies on another stack.

We could declare relationships between stacks. This would allow a CI/CD system to quickly start the plan/approve/apply process for dependant stacks. However, this requires extra work for the project maintainers, and the only benefit this has over triggering drift detection for all stacks is that it would be faster. Unless the project has a very large number of stacks, it is probably not worth the complication of introducing the concept of stack dependencies.


* Pull request usage:
    * Adding a comment with `/plan` to a pull request creates a GitHub deployment, creates Terraform plans, and stores them as artifacts.
        * GitHub Deployments don't actually do anything. They are designed for situations like this where you want to manage and track deployments.
        * One deployment is created per directory being planned.
        * If there is an active deployment for a directory from another pull request, the command fails with an error saying that it is in use by the other pull request.
    * Adding a comment with `/apply` to a pull request will apply the changes in the plan files and delete the plan files.
        * What if someone does a plan for dir1, pushes a change, does a plan for dir2, pushes a change, etc? Only apply last plan, or do plans accumulate?
        * Applying a change does not automatically finish the active deployments.
    * Closing or merging the pull request finishes the active deployments and deletes any remaining plans.
        * It does not automatically apply changes.
    * Adding a comment with `/clear` (or something) to a pull request will delete plans and end active deployments.
    * This workflow involves applying changes *before* merging them into the master branch.
        * If done the other way around, you might merge, then apply, then not notice errors from the apply.
* Drift detection.
  * Runs on a schedule.
  * Creates empty pull requests with plans if it finds unapplied changes.
  * Checks 1 directory each time it runs, not all of them together, to avoid blocking usage in pull requests.
  * Runs often so it checks every directory often enough.
  * Directories are skipped when there are active deployments in pull requests.



/plan
    for each changed stack:
        create github deployment for this pr + stack
    clear other github deployments from this pr
    delete all artifacts from this pr
    for each changed stack:
        create terraform plan and store as artifact

/apply
    for each github deployment from this pr:
        download tfplan artifact
        terraform apply tfplan
        complete github deployment
