import uuid
from dataclasses import dataclass
from typing import Generator, Optional, Sequence, Union, Any, Protocol

import pytest
from _pytest.fixtures import SubRequest

from integration.conftest import CollectionFactory
from weaviate import Collection
from weaviate.collections.classes.config import (
    Configure,
    DataType,
    Property,
    ReferenceProperty,
)
from weaviate.collections.classes.internal import (
    Reference,
    _CrossReference,
    FromReference,
)
from weaviate.collections.classes.tenants import Tenant

UUID = Union[str, uuid.UUID]


@dataclass
class MockNumpyTorch:
    array: list

    def squeeze(self) -> "MockNumpyTorch":
        return self

    def tolist(self) -> list:
        return self.array


@dataclass
class MockTensorFlow:
    array: list

    def numpy(self) -> "MockNumpyTorch":
        return MockNumpyTorch(self.array)


UUID1 = uuid.UUID("806827e0-2b31-43ca-9269-24fa95a221f9")
UUID2 = uuid.UUID("8ad0d33c-8db1-4437-87f3-72161ca2a51a")
UUID3 = uuid.UUID("83d99755-9deb-4b16-8431-d1dff4ab0a75")
UUID4 = uuid.UUID("385c992b-452a-4f71-a5d9-b161f51b540d")
UUID5 = uuid.UUID("0a4d16b3-c418-40d3-a6b7-51f87c7a603b")
UUID6 = uuid.UUID("c8a201b6-fdd2-48d1-a8ee-289a540b1b4b")


class BatchCollection(Protocol):
    """Typing for fixture."""

    def __call__(self, name: str = "", multi_tenancy: bool = False) -> Collection[Any, Any]:
        """Typing for fixture."""
        ...


@pytest.fixture
def batch_collection(
    collection_factory: CollectionFactory,
) -> Generator[BatchCollection, None, None]:
    def _factory(name: str = "", multi_tenancy: bool = False) -> Collection[Any, Any]:
        collection = collection_factory(
            name=name,
            vectorizer_config=Configure.Vectorizer.none(),
            properties=[
                Property(name="name", data_type=DataType.TEXT),
                Property(name="age", data_type=DataType.INT),
            ],
            multi_tenancy_config=Configure.multi_tenancy(multi_tenancy),
        )
        collection.config.add_reference(
            ReferenceProperty(name="test", target_collection=collection.name)
        )

        return collection

    yield _factory


@pytest.mark.parametrize(
    "vector",
    [None, [1, 2, 3], MockNumpyTorch([1, 2, 3]), MockTensorFlow([1, 2, 3])],
)
@pytest.mark.parametrize("uuid", [None, UUID1, str(UUID2), UUID3.hex])
def test_add_object(
    batch_collection: BatchCollection,
    uuid: Optional[UUID],
    vector: Optional[Sequence],
) -> None:
    collection = batch_collection()

    with collection.batch as batch:
        batch.add_object(
            uuid=uuid,
            vector=vector,
        )
        assert batch.num_objects() == 1
        assert batch.num_references() == 0
    assert len(batch.failed_objects()) == 0
    assert len(batch.failed_references()) == 0
    objs = collection.query.fetch_objects().objects
    assert len(objs) == 1


@pytest.mark.parametrize("from_uuid", [UUID1, str(UUID2), UUID3.hex])
@pytest.mark.parametrize("to_uuid", [UUID4.hex, UUID5, str(UUID6)])
def test_add_reference(
    batch_collection: BatchCollection,
    request: SubRequest,
    from_uuid: UUID,
    to_uuid: UUID,
) -> None:
    """Test the `add_reference` method"""
    collection = batch_collection()

    with collection.batch as batch:
        batch.add_object(uuid=from_uuid)
        assert batch.num_objects() == 1
        assert batch.num_references() == 0
        batch.add_object(uuid=to_uuid)
        assert batch.num_objects() == 2
        assert batch.num_references() == 0
        batch.add_reference(from_uuid=from_uuid, from_property="test", to=Reference.to(to_uuid))
        assert batch.num_objects() == 2
        assert batch.num_references() == 1
    assert len(batch.failed_objects()) == 0
    assert len(batch.failed_references()) == 0
    objs = collection.query.fetch_objects().objects
    obj = collection.query.fetch_object_by_id(
        from_uuid, return_references=FromReference(link_on="test")
    )
    assert len(objs) == 2
    assert isinstance(obj.references["test"], _CrossReference)


def test_add_object_batch_with_tenant(batch_collection: BatchCollection) -> None:
    mt_collection = batch_collection(multi_tenancy=True)

    mt_collection.tenants.create([Tenant(name="tenant" + str(i)) for i in range(5)])
    for i in range(5):
        with mt_collection.with_tenant("tenant" + str(i % 5)).batch as batch:
            batch.add_object(
                properties={"name": "tenant" + str(i % 5)},
            )
    assert len(batch.failed_objects()) == 0
    assert len(batch.failed_references()) == 0
    objs = mt_collection.with_tenant("tenant1").query.fetch_objects().objects
    assert len(objs) == 1
    for obj in objs:
        assert obj.properties["name"] == "tenant1"


def test_add_ref_batch_with_tenant(batch_collection: BatchCollection) -> None:
    mt_collection = batch_collection(multi_tenancy=True)

    mt_collection.tenants.create([Tenant(name="tenant" + str(i)) for i in range(5)])

    with mt_collection.with_tenant("tenant1").batch as batch:
        obj_uuid0 = uuid.uuid4()
        batch.add_object(properties={"name": "one"}, uuid=obj_uuid0)

        obj_uuid1 = uuid.uuid4()
        batch.add_object(
            properties={"name": "two"},
            uuid=obj_uuid1,
        )

        # add refs between classes for all tenants
        batch.add_reference(
            from_property="test",
            from_uuid=obj_uuid1,
            to=Reference.to_multi_target(obj_uuid0, target_collection=mt_collection.name),
        )
        batch.add_reference(
            from_property="test",
            from_uuid=obj_uuid0,
            to=Reference.to_multi_target(obj_uuid1, target_collection=mt_collection.name),
        )
        # target collection required when inserting references into multi-tenancy collections
    assert len(batch.failed_objects()) == 0
    assert len(batch.failed_references()) == 0
    ret_obj = mt_collection.with_tenant("tenant1").query.fetch_object_by_id(
        obj_uuid0, return_references=FromReference(link_on="test")
    )
    assert ret_obj.properties["name"] == "one"
    assert isinstance(ret_obj.references["test"], _CrossReference)
