import logging
from collections.abc import Callable
from typing import Any, Optional

import attrs
from core.abstracts.models import ModelBase
from django.db.migrations import serializer
from drf_spectacular.types import PYTHON_TYPE_MAPPING, OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import exceptions, serializers
from rest_framework.request import Request

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
                                return parse_date(raw, fail_silently=True)
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


def params_validator(
    validator_class: serializer.Serializer,
    query_params: list[str] = None,
    path_params: list[str] = None,
):
    """
    Validates params based on a serializer class before they are passed to an endpoint.

    Validates an instance exists for an object id if pk is in path params. Returns the instance into kwargs as "instance".

    Example:
    ```
        @params_validator(ClubPreviewRetrieveValidator, path_params=["pk"], query_params=["is_csu_partner"])
        def retrieve(self, request: Request, *args, **kwargs):
            club_id = self.kwargs.get("pk")
            result = check_cache(DETAIL_CLUB_PREVIEW_PREFIX, club_id=club_id)

            if not result:
                club = kwargs.get("instance")
                result = ClubPreviewSerializer(club).data
                set_cache(result, DETAIL_CLUB_PREVIEW_PREFIX, club_id=club_id)

            return Response(result)
    """

    def decorator[T: Callable](callable: T) -> T:
        def wrapper(*f_args, **f_kwargs):
            request: Request = f_args[0].request

            if request is None:
                logging.error(
                    "params_validator decorated on method that does not have a request field on its instance"
                )
                raise exceptions.APIException("Internal Server Error", 500)

            request_query_params = dict(request.query_params.copy())
            params: dict = {}
            if query_params:
                for q in query_params:
                    # Why is this a list
                    val = request_query_params.get(q, None)
                    params[q] = val[0] if val else val

            if path_params:
                for p in path_params:
                    params[p] = f_kwargs.get(p, None)

            try:
                serializer = validator_class(data=params)
                serializer.is_valid(raise_exception=True)
            except ValueError as e:
                print(e.args)
                raise exceptions.ValidationError() from e

            # Check if the object exists and throw 404 for retrieve type endpoints
            instance: ModelBase = None
            if path_params and "pk" in path_params:
                id = params["pk"]
                model: ModelBase = None
                try:
                    model = f_args[0].queryset.model

                except AttributeError as e:
                    logging.error(
                        "params_validator decorated on method that does not have a queryset on its instance"
                    )
                    raise exceptions.APIException("Internal Server Error", 500) from e

                try:
                    if model is None:
                        logging.error(
                            "params_validator decorated on method that does not have a model on its instance"
                        )
                        raise exceptions.APIException("Internal Server Error", 500)

                    instance = model.objects.get_by_id(id)

                except model.DoesNotExist as e:
                    raise exceptions.NotFound(
                        f"{model._meta.model_name} not found with id: " + id, 404
                    ) from e

            return callable(*f_args, **f_kwargs, instance=instance)

        return wrapper

    return decorator


def parse_bool_param(value: str | None, field_name: str = "param") -> bool | None:
    """Converts bool query param to correct boolean representation due to weird coercion behavior"""
    if value is None:
        return value

    if value.lower() in {"true", "1"}:
        return True
    elif value.lower() in {"false", "0"}:
        return False

    raise serializers.ValidationError(
        {field_name: "Must be coercible a boolean value."}
    )
