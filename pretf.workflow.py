from pretf import workflow


def pretf_workflow(root_module=None):
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
