def pretf_variables(var):
    yield {
        "enable_dns_support": True,
        "enable_dns_hostnames": True,
        "stack": "vpc",
        "tags": {"Name": f"pretf-example-project-{var.environment}"},
    }


# test
