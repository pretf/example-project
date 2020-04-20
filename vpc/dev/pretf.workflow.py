from pretf import workflow


def pretf_workflow():
    return workflow.load_parent(
        root_module={
            "source": "claranet/vpc-modules/aws//modules/vpc",
            "version": "1.1.0",
        }
    )
