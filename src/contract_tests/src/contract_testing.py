from collections import defaultdict
from typing import Dict, List, cast, Callable
from pydantic import BaseModel
from enum import Enum
from hypothesis import strategies as st
import datetime


# maps actual base model to the spec name it consumes
# could maybe be other way around (i.e spec and it's consumers?)
# {class <thing>: "feed/v1/{account_id}/account-settings" }
MODEL_MAP: Dict[BaseModel, Dict] = defaultdict(Dict)


# todo - move to a common place
class HTTPMethod(Enum):
    # mad this isn't in standard lib
    DELETE = "delete"
    GET = "get"
    POST = "post"
    PUT = "put"


def is_consumer_of(spec_path: str, method: HTTPMethod, code: int):
    """Registers a type as being a consumer of an API"""
    def wrapper(cls):
        # MODEL_MAP[cls] = spec_name
        MODEL_MAP[cls] = {"spec_path": spec_path, "method": method, "code": code}
        return cls
    return wrapper


FIELD_TYPES = {
    "boolean": st.booleans,
    "integer": st.integers,
    "number": lambda: st.decimals(allow_nan=False, allow_infinity=False).map(
        lambda x: str(x)
    ),
    "object": lambda: st.dictionaries(keys=st.text(), values=st.text()),
    "null": st.none,
}


def get_string_format_strategy(schema: dict) -> st.SearchStrategy:
    string_format = schema["format"]

    if string_format == "date":
        return st.dates(min_value=datetime.date(1000, 1, 1)).map(
            lambda x: x.isoformat()
        )
    elif string_format == "date-time":
        return st.datetimes(min_value=datetime.datetime(1000, 1, 1, 0, 0)).map(
            lambda x: x.isoformat() + "+00:00"
        )
    elif string_format == "uuid":
        return st.uuids().map(lambda x: str(x))

    return st.text(min_size=1)


def get_string_strategy(schema: dict) -> st.SearchStrategy:
    if "enum" in schema:
        if "format" in schema and schema["format"] == "restrictive-string":
            return st.sampled_from(
                [v for v in schema["enum"] if not v.startswith("regex")]
            )
        return st.sampled_from(schema["enum"])
    elif "format" in schema:
        return get_string_format_strategy(schema)

    return st.text(min_size=1)


def get_schema_strategy(
    schema: dict
) -> st.SearchStrategy:
    if "oneOf" in schema:
        return st.one_of(
            *[
                get_schema_strategy(one)
                for one in schema["oneOf"]
                if one["type"] != "null"
            ]
        )
    if "anyOf" in schema:
        return st.one_of(
            *[
                get_schema_strategy(one)
                for one in schema["anyOf"]
                if one["type"] != "null"
            ]
        )

    if type(schema.get("items")) is list:
        for i in schema["items"]:
            return get_schema_strategy(i)

    elif schema["type"] == "object" and "properties" in schema:
        return st.fixed_dictionaries(
            {
                key: get_schema_strategy(schema["properties"][key])
                for key in schema["properties"]
            }
        )
    elif schema["type"] == "array":
        return st.lists(
            get_schema_strategy(schema["items"]),
            min_size=schema.get("minItems", 0),
            max_size=schema.get("maxItems", 3),
            unique=schema.get("uniqueItems", False),
        )
    elif schema["type"] == "string":
        return get_string_strategy(schema)
    elif schema["type"] in FIELD_TYPES:
        return cast(
            Callable[[], st.SearchStrategy], FIELD_TYPES[schema["type"]]
        )()

    raise NotImplementedError(
        "Unknown property type {}".format(schema["type"])
    )