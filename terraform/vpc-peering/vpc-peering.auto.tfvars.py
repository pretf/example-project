from pretf.api import get_outputs


def pretf_variables(var):
    dev = get_outputs("../../vpc/dev")
    stage = get_outputs("../../vpc/stage")
    prod = get_outputs("../../vpc/prod")
    yield {
        "dev_vpc_id": dev["vpc_id"],
        "stage_vpc_id": stage["vpc_id"],
        "prod_vpc_id": prod["vpc_id"],
        "stack": "vpc-peering",
    }
