from dataclasses import dataclass
from typing import Dict, List, Optional, Generic
from weaviate.collections.classes.internal import P, R
from weaviate.collections.classes.types import _WeaviateInput
from weaviate.types import UUID


@dataclass
class Error:
    """This class represents an error that occurred when attempting to insert an object within a batch."""

    message: str
    code: Optional[int] = None
    original_uuid: Optional[UUID] = None


@dataclass
class RefError:
    """This class represents an error that occurred when attempting to insert a reference between objects within a batch."""

    message: str


@dataclass
class DataObject(Generic[P, R]):
    """This class represents an entire object within a collection to be used when batching."""

    properties: Optional[P] = None
    uuid: Optional[UUID] = None
    vector: Optional[List[float]] = None
    references: Optional[R] = None


@dataclass
class DataReference:
    """This class represents a reference between objects within a collection to be used when batching."""

    from_property: str
    from_uuid: UUID
    to_uuid: UUID


class GeoCoordinate(_WeaviateInput):
    """Input for the geo-coordinate datatype."""

    latitude: float
    longitude: float

    def _to_dict(self) -> Dict[str, float]:
        return {"latitude": self.latitude, "longitude": self.longitude}