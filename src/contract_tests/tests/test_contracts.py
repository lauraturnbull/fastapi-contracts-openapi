import pytest
from src.contract_tests.src.contract_testing import MODEL_MAP, get_schema_strategy
import jsonref
from pathlib import Path
from typing import Dict, Type
from pydantic import BaseModel
from hypothesis import given

# import to register the tests
from src.fake_service.core import types


def load_specs() -> Dict[str, dict]:
    specs = {}
    directory = Path(__file__).parent.parent / "specs"
    for service_spec in directory.rglob("*.json"):
        with open(service_spec, "r") as f:
            # {feed: {full feed spec}}
            specs[service_spec.parent.name] = jsonref.loads(f.read())
    return specs

# {"feed": {full api spec}}
SPECS_MAP = load_specs()


# need to trim model map to first slash
@pytest.mark.parametrize(
    ["base_model", "consumed_spec"],
    [
        (base_model, consumed_spec)
        for base_model, consumed_spec in MODEL_MAP.items()
    ],
    # ids=[".".join([k.__module__, k.__name__]) for k in MODEL_MAP], used for displaying test results
)
def test_contracts(
    base_model: Type[BaseModel], consumed_spec: dict
):
    service, path = consumed_spec["spec_path"].split("/", 1)
    path = "/" + path
    method = consumed_spec["method"].value
    code = str(consumed_spec["code"])

    service_spec = SPECS_MAP[service]["paths"]
    try:
        response = service_spec[path][method]["responses"][code]
    except KeyError:
        raise Exception(f"No API spec for {service} {method} {code} found.")

    schema = response["content"]["application/json"]["schema"]

    strategy = get_schema_strategy(schema)

    @given(strategy)
    def test_contract(data):
        if issubclass(schema, BaseModel):
            assert schema(**data)

    test_contract()