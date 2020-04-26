from unittest.mock import ANY

import pytest
from pretf import test


class TestProject(test.SimpleTest):
    @pytest.mark.parametrize(
        "stack,env,expected",
        [
            (
                "vpc",
                "dev",
                {
                    "internet_gateway_id": ANY,
                    "vpc_cidr_block": "10.1.0.0/16",
                    "vpc_id": ANY,
                },
            ),
            (
                "vpc",
                "stage",
                {
                    "internet_gateway_id": ANY,
                    "vpc_cidr_block": "10.2.0.0/16",
                    "vpc_id": ANY,
                },
            ),
            (
                "vpc",
                "prod",
                {
                    "internet_gateway_id": ANY,
                    "vpc_cidr_block": "10.3.0.0/16",
                    "vpc_id": ANY,
                },
            ),
            (
                "vpc-peering",
                "prod",
                {"prod_to_stage_status": "active", "stage_to_dev_status": "active"},
            ),
        ],
    )
    def test_apply(self, stack, env, expected):
        self.pretf(f"terraform/{stack}/{env}").init()
        outputs = self.pretf(f"terraform/{stack}/{env}").apply()
        assert outputs == expected

    @test.always
    @pytest.mark.parametrize(
        "stack,env",
        [("vpc-peering", "prod"), ("vpc", "dev"), ("vpc", "prod"), ("vpc", "stage")],
    )
    def test_destroy(self, stack, env):
        self.pretf(f"terraform/{stack}/{env}").destroy()
