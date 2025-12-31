from collections.abc import Callable
from typing import Any, Optional

import attr
from drf_spectacular.types import PYTHON_TYPE_MAPPING, OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema


@attr.s
class Query:
    """Settings for a single query param."""

    qtype: type = attr.ib(
        default=OpenApiTypes.STR,
        converter=lambda t: PYTHON_TYPE_MAPPING.get(t, OpenApiTypes.STR),
    )
    default: Optional[Any] = attr.ib(default=None)
    description: Optional[str] = attr.ib(default=None)
    required: bool = attr.ib(default=False)
    is_list: bool = attr.ib(default=False)


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
                        if value.is_list:
                            query_value = request.GET.getlist(key, None) or None

                            if value.qtype == OpenApiTypes.INT:
                                query_value = [int(item) for item in query_value]

                        else:
                            query_value = request.GET.get(key, None)

                            if value.qtype == OpenApiTypes.INT:
                                query_value = int(query_value)

                        query_values[key] = query_value
            except Exception:
                pass

            return callable(*f_args, **f_kwargs, **query_values)

        return wrapper

    return decorator
