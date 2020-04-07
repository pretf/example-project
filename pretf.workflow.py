"""
Initial simple idea for GitHub Actions:

* Create a pull request
* Add comment "/plan" or "/plan vpc/dev" to run plans.
* Plans get uploaded to S3 under location "{pr}/{stack}/tfplan"
* Add comment "/apply"
* It refuses if the PR hasn't been approved (and merged?)
* Otherwise, it downloads plans from S3 and applies them

"""

import os
import subprocess
from pathlib import Path

from pretf import workflow


def get_all_stacks():
    stacks = set()
    for path in Path(".").rglob("terraform.tfvars"):
        name = str(path.parent)
        if not name.startswith("."):
            stacks.add(name)
    return sorted(stacks)


def get_changed_files():
    default_branch = f"origin/{os.environ['DEFAULT_BRANCH']}"
    return sorted(
        subprocess.check_output(["git", "diff", "--name-only", default_branch])
        .decode()
        .splitlines()
    )


def get_changed_stacks():
    changed_stacks = set()
    unchanged_stacks = set(get_all_stacks())
    for changed_file in get_changed_files():
        changed_dir = str(Path(changed_file).parent)
        for name in list(unchanged_stacks):
            if f"{name}/".startswith(f"{changed_dir}/"):
                changed_stacks.add(name)
                unchanged_stacks.remove(name)
        if not unchanged_stacks:
            break
    return sorted(changed_stacks)


def github_action(comment):

    parts = comment.split()
    if parts and parts[0] == "/plan":
        stacks = parts[1:]
        if not stacks:
            stacks = get_changed_stacks()
        elif "*" in stacks:
            stacks = get_all_stacks()
        success, output = github_plan(stacks)
    else:
        raise ValueError(comment)

    if success:
        name = "github-output"
    else:
        name = "github-error"
    with open(name, "w") as open_file:
        open_file.write(output)

    return 0 if success else 1


def github_plan(stacks):
    success = True
    markdown = []

    env = os.environ.copy()
    del env["GITHUB_COMMENT"]
    env["TF_IN_AUTOMATION"] = "1"

    for stack in stacks:

        markdown.append(f"# {stack}")

        proc = subprocess.run(
            ["pretf", "init", "-input=false", "-no-color"],
            cwd=stack,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if proc.returncode != 0:
            error = True
            output = proc.stdout.decode()
            print(output)
            markdown.append(f"```\n{output.strip()}\n```")
            break

        proc = subprocess.run(
            ["pretf", "plan", "-input=false", "-no-color", "-out=tfplan"],
            cwd=stack,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        output = proc.stdout.decode()
        print(output)
        markdown.append(f"```\n{output.strip()}\n```")

        if proc.returncode != 0:
            success = False
            break

    return success, "\n\n".join(markdown)


def pretf_workflow(root_module=None):
    if os.environ.get("GITHUB_COMMENT"):
        return github_action(os.environ["GITHUB_COMMENT"])

    # Check that the working directory contains a terraform.tfvars file.
    # Those are the only directories which are set up to run Terraform.
    # An error will be displayed when running from the wrong directory.
    workflow.require_files("terraform.tfvars")

    # Clean up files and links from previous failed executions.
    workflow.delete_files()
    workflow.delete_links()

    # Link these files into the working directory
    # as they are used by all stacks and environments.
    created = workflow.link_files("*.tf", "*.tf.py", "*.tfvars", "*.tfvars.py")

    # Link this root module into the working directory. The details must
    # be passed in by the pretf.workflow.py files in the stack directories
    # (different stacks can specify different modules).
    if root_module:
        created += workflow.link_module(**root_module)

    # Create *.tf.json and *.tfvars.json files
    # from *.tf.py and *.tfvars.py files.
    created += workflow.create_files()

    # Execute Terraform, raising an exception if it fails.
    proc = workflow.execute_terraform()

    # If it got this far, then it was successful.
    # Clean up all of the files that were created.
    workflow.clean_files(created)

    # Return the execution result.
    return proc
