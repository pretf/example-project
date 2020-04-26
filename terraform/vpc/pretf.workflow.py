from pretf import workflow


def pretf_workflow(root_module=None):
    if not root_module:
        root_module = {
            "source": "claranet/vpc-modules/aws//modules/vpc",
            "version": "1.0.0",
        }
    return workflow.load_parent(root_module=root_module)
