from typing import Generic

from core.abstracts.models import ModelBase
from utils.types import T


class ServiceBase(Generic[T]):
    model = ModelBase
    obj: T

    str_lookup = "id"

    def __init__(self, obj: T | int | str) -> None:
        if isinstance(obj, int) or (isinstance(obj, str) and obj.isnumeric()):
            obj = self.model.objects.find_by_id(obj)
        elif isinstance(obj, str):
            obj = self.model.objects.find_one(**{self.str_lookup: obj})

        self.obj = obj

        super().__init__()
