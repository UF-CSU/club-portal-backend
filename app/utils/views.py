from collections.abc import Callable
from typing import Any, Optional

import attrs
from drf_spectacular.types import PYTHON_TYPE_MAPPING, OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema

from utils.dates import parse_date
from utils.logging import print_error


@attrs.define
class Query:
    """Settings for a single query param."""

    qtype: type = attrs.field(default=str)
    default: Optional[Any] = attrs.field(default=None)
    description: Optional[str] = attrs.field(default=None)
    required: bool = attrs.field(default=False)
    is_list: bool = attrs.field(default=False)

    @property
    def openapi_type(self):
        return PYTHON_TYPE_MAPPING.get(self.qtype, OpenApiTypes.STR)


def query_params(**kwargs: Query):
    """
    Apply query params to a route, and add to swagger schema.

    Query params can be accessed via kwargs, or request.GET.

    Example:
    ```
    class TestView(...):
        @query_params(
            query_one=Query(required=True, description="Lorem ipsum"),
            another_query=Query(qtype=int, default=0),
            third_query=Query()
        )
        def get(self, *args, query_one, another_query=None, third_query=None, **kwargs):
            pass
    """

    def decorator[T: Callable](callable: T) -> T:
        @extend_schema(
            parameters=[
                OpenApiParameter(
                    name=key,
                    type=value.qtype,
                    location=OpenApiParameter.QUERY,
                    description=value.description,
                    required=value.required,
                    many=value.is_list,
                )
                for key, value in kwargs.items()
            ]
        )
        def wrapper(*f_args, **f_kwargs):
            query_values = {}

            try:
                request = f_args[1]
                if request:
                    for key, value in kwargs.items():
                        query_value = None

                        def _parse_value(raw, value=value):
                            if value.qtype is int:
                                return int(raw)
                            elif (
                                value.qtype.__name__ == "date"
                            ):  # Type equality doesn't work for some reason
                                return parse_date(raw, fail_silently=False)
                            else:
                                return raw

                        if value.is_list:
                            query_value = request.GET.getlist(key, None) or None
                            query_value = (
                                [_parse_value(item) for item in query_value]
                                if query_value is not None
                                else None
                            )

                        else:
                            query_value = request.GET.get(key, None)
                            query_value = _parse_value(query_value)

                        query_values[key] = query_value
            except Exception:
                print_error()
                pass

            return callable(*f_args, **f_kwargs, **query_values)

        return wrapper

    return decorator
