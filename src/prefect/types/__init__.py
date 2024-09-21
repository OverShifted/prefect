from functools import partial
from typing import Annotated, Any, Dict, List, Type, TypeVar, Union
import orjson
import pydantic

from pydantic import (
    BeforeValidator,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    TypeAdapter,
)
from zoneinfo import available_timezones

T = TypeVar("T")

MAX_VARIABLE_NAME_LENGTH = 255
MAX_VARIABLE_VALUE_LENGTH = 5000

NonNegativeInteger = Annotated[int, Field(ge=0)]
PositiveInteger = Annotated[int, Field(gt=0)]
NonNegativeFloat = Annotated[float, Field(ge=0.0)]

TimeZone = Annotated[
    str,
    Field(
        default="UTC",
        pattern="|".join(
            [z for z in sorted(available_timezones()) if "localtime" not in z]
        ),
    ),
]


BANNED_CHARACTERS = ["/", "%", "&", ">", "<"]

WITHOUT_BANNED_CHARACTERS = r"^[^" + "".join(BANNED_CHARACTERS) + "]+$"
Name = Annotated[str, Field(pattern=WITHOUT_BANNED_CHARACTERS)]

WITHOUT_BANNED_CHARACTERS_EMPTY_OK = r"^[^" + "".join(BANNED_CHARACTERS) + "]*$"
NameOrEmpty = Annotated[str, Field(pattern=WITHOUT_BANNED_CHARACTERS_EMPTY_OK)]


def non_emptyish(value: str) -> str:
    if not value.strip("' \""):
        raise ValueError("name cannot be an empty string")

    return value


NonEmptyishName = Annotated[
    str,
    Field(pattern=WITHOUT_BANNED_CHARACTERS),
    BeforeValidator(non_emptyish),
]


VariableValue = Union[
    StrictStr,
    StrictInt,
    StrictBool,
    StrictFloat,
    None,
    Dict[str, Any],
    List[Any],
]


def check_variable_value(value: object) -> object:
    try:
        json_string = orjson.dumps(value)
    except orjson.JSONEncodeError:
        raise ValueError("Variable value must be serializable to JSON")

    if value is not None and len(json_string) > MAX_VARIABLE_VALUE_LENGTH:
        raise ValueError(
            f"Variable value must be less than {MAX_VARIABLE_VALUE_LENGTH} characters"
        )
    return value


StrictVariableValue = Annotated[VariableValue, BeforeValidator(check_variable_value)]

LaxUrl = Annotated[str, BeforeValidator(lambda x: str(x).strip())]

StatusCode = Annotated[int, Field(ge=100, le=599)]


class SecretDict(pydantic.Secret[Dict[str, Any]]):
    pass


def validate_list_T_from_delim_string(
    value: Union[str, T, List[T], None], type_, delim=None
) -> List[T]:
    """
    "no-info" before validator useful in scooping env vars

    e.g. `PREFECT_CLIENT_RETRY_EXTRA_CODES=429,502,503` -> `[429, 502, 503]`
    e.g. `PREFECT_CLIENT_RETRY_EXTRA_CODES=429` -> `[429]`
    """
    if not value:
        return []
    delim = delim or ","
    if isinstance(value, str):
        return [TypeAdapter(type_).validate_strings(s) for s in value.split(delim)]
    errors = []
    try:
        return [TypeAdapter(type_).validate_python(value)]
    except pydantic.ValidationError as e:
        errors.append(e)
    try:
        return TypeAdapter(List[type_]).validate_python(value)
    except pydantic.ValidationError as e:
        errors.append(e)
    raise ValueError(f"Invalid list[{type_}]: {errors}")


ClientRetryExtraCodes = Annotated[
    Union[str, StatusCode, List[StatusCode], None],
    BeforeValidator(partial(validate_list_T_from_delim_string, type_=StatusCode)),
]

__all__ = [
    "ClientRetryExtraCodes",
    "NonNegativeInteger",
    "PositiveInteger",
    "NonNegativeFloat",
    "Name",
    "NameOrEmpty",
    "NonEmptyishName",
    "SecretDict",
    "StatusCode",
    "StrictVariableValue",
]
