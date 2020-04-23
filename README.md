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

<details>
  <summary>Is this similar to Terragrunt?</summary>

  Many of the features and goals of this example, and Pretf itself, are inspired and influenced by [Terragrunt](https://terragrunt.gruntwork.io/). They have some good ideas. Some reasons to choose Pretf are:

  * Pretf has better support for AWS credentials.
    * Supports multiple AWS providers in the same stack, using multiple MFA-protected profiles. This results in much simpler Terraform code when dealing with cross-account VPC peering, cross-account Route 53 zone delegation, etc.
  * Pretf lets you generate complex Terraform configuration with Python code.
    * This is completely optional, many projects do not need this.
  * Pretf lets you configure everything with Python code.
    * This is completely optional, but recommended.
    * This example demonstrates just one way to augment a Terraform project. You can write your own `pretf.workflow.py` file(s) and do anything you want.
</details>

## Hierarchical project structure

The CI/CD system should detect which stacks have changed with [git-diff-terraform-dirs.py](./git-diff-terraform-dirs.py) and plan/apply from those directories. This section goes into detail about how this works, and why projects should be structured in a *hierarchical* way.

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

<details>
  <summary>Why not try harder to detect changes in this structure?</summary>

  It is true, [terraform-diff](https://github.com/contentful-labs/terraform-diff) or similar approaches could work, but it would require making assumptions about project structures, or it would need lots of options and documentation for it to be flexible enough to be useful. Let's keep things simple and assume a hierarchical project structure.
</details>

Now let's consider this hierarchical project structure:

```
iam/
    main.tf
    dev/
        terraform.tfvars
    stage/
        terraform.tfvars
    prod/
        terraform.tfvars
vpc/
    main.tf
    dev/
        terraform.tfvars
    stage/
        terraform.tfvars
    prod/
        terraform.tfvars
vpc-peering/
    main.tf
    dev/
        terraform.tfvars
    stage/
        terraform.tfvars
    prod/
        terraform.tfvars
```

The hierarchy of this project makes it easy to determine the directories to plan/apply when files have changed. If `vpc/main.tf` has changed then it will potentially affect all directories below it: `vpc/dev` and `vpc/prod`. If `vpc/dev/terraform.tfvars` has changed then it will only affect the `vpc/dev` directory, as there are no directories below it.

<details>
  <summary>Where did the <code>tags</code> module from the first structure go?</summary>

  Let's say that the module was only used by the `vpc` directory and it was very simple. In this case, we'd just move it into `vpc/tags.tf`. Just like `vpc/main.tf`, changes to `vpc/tags.tf` will potentially affect the directories below it: `vpc/dev` and `vpc/prod`.

  Let's say that the module was used by both the `vpc` and `vpc-peering` directories. In this case, we'd move the module into a separate git repository, then `vpc/main.tf` and `vpc-peering/main.tf` would include it as a versioned remote module. When changes are made to the `tags` module repository, and a new version is released, we would update `vpc/main.tf` and `vpc-peering/main.tf` to use the new version. We can now determine that all directories below `vpc` and `vpc-peering` have potentially changed, but the `iam` directories have not.
</details>

## Making changes to specific environments

When submitting a pull request, the CI/CD system should plan and apply all affected directories together. This encourages having **everything** in the master branch applied immediately, which in turn discourages people from pushing changes that affect multiple environments at the same time.

If a CI/CD system has multiple deployment stages (for example: deploy to dev, wait for approval, deploy to stage, wait for approval, deploy to prod) then *the desired state of the infrastructure is hidden within the current state of the CI/CD system*.

If you don't have a CI/CD system, and you're manually applying a Terraform change across multiple environments and testing each one as you go, then *the desired state of the infrastructure is hidden within your head*.

Applying all changes together makes the desired state of the infrastructure more clear, encourages better development practices and reduces the occurrences of changes blocking each other.

How does it work? Let's start with this structure:

```
vpc/
    main.tf
    dev/
        terraform.tfvars
    stage/
        terraform.tfvars
    prod/
        terraform.tfvars
```

If you make a change to `vpc/main.tf`, the CI/CD system should plan/apply `vpc/dev`, `vpc/stage` and `vpc/prod` together. This practically forces people into making sure that their pull requests and changes only affect one environment at a time.

Here are 3 ways to reduce the scope of a change so that it only affects one environment:

### Conditional logic

You can start by putting conditional logic directly in your Terraform code. Actually, try not to do this because it is messy.

```hcl
# vpc/main.tf

resource "aws_vpc" "this" {
  cidr_block           = var.cidr_block
  enable_dns_support   = var.env == "dev" || var.env == "stage"
  enable_dns_hostnames = var.env == "dev"
}
```

### Feature flags

A better way is to use feature flag variables. Define the feature flags and enable or disable them in `.tfvars` files.

```hcl
# vpc/main.tf

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
```

```hcl
# dev/terraform.tfvars

enable_dns_support = true
enable_dns_hostnames = true
```

```hcl
# stage/terraform.tfvars

enable_dns_support = true
```

### Versioned remote modules

Another way is to use versioned remote modules with Pretf. This requires a different project structure, replacing `main.tf` with custom Pretf workflows that fetch different versions of the VPC module depending on the environment. The [vpc](vpc) directory of this repository demonstrates how this can be done.

## Drift detection

There are multiple ways for the infrastructure and code to "drift" apart.

1. An external process (such as a user in the AWS console) changes the infrastructure.
2. Changes have been made to one directory which indirectly affects another directory.

We cannot reasonably fully prevent the first scenario from happening, so we want some form of drift detection for all Terraform directories in the project. This would need to run on a regular schedule (e.g. every hour) because we don't know when changes might happen.

The second scenario is likely to happen in many projects. Ideally, the system would automatically detect which dependant directories need updating after changes have been applied, but it is impossible to make this 100% accurate. Consider a Terraform directory that creates a CloudFormation stack that creates a Lambda function custom resource that performs a lookup on a resource created by another Terraform directory. There is no way to reliably determine that one directory relies on another.

We could declare relationships between directories. This would allow a CI/CD system to quickly start the plan/apply process for dependant directories. However, this requires extra work for the project maintainers, and the only benefit this has over triggering drift detection is that it would be faster. Unless the project has a very large number of Terraform directories, or it is especially time-sensitive, it is probably not worth the complication of introducing the concept of dependencies.

## GitHub Actions (ignore this)

Here are some ideas for how GitHub Actions might work.

* scheduled action:
    * plan next directory in sequence
    * if changes, create pull request with plan

* pull request actions:
    * create
        * same as /start
    * sync
        * same as /stop then /start

* comment on pull request:
    * /add `<dir>`
        * create plan for `<dir>`
    * /remove `<dir>`
        * delete plan for `<dir>`
    * /stop
        * delete all plans
    * /start
        * detect changed directories
        * create plans for them
    * apply
        * apply all plans
