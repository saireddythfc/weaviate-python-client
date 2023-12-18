import pathlib
from typing import Generator

import pytest

import weaviate
from weaviate.collections.classes.aggregate import (
    AggregateBoolean,
    AggregateDate,
    AggregateInteger,
    AggregateNumber,
    AggregateText,
    Metrics,
)
from weaviate.collections.classes.config import DataType, Property, ReferenceProperty, Configure
from weaviate.exceptions import WeaviateInvalidInputException, WeaviateQueryException
from weaviate.util import file_encoder_b64


@pytest.fixture(scope="module")
def client() -> Generator[weaviate.WeaviateClient, None, None]:
    client = weaviate.connect_to_local()
    client.collections.delete_all()
    yield client
    client.collections.delete_all()


@pytest.mark.parametrize("how_many", [1, 10000, 20000, 20001, 100000])
def test_collection_length(client: weaviate.WeaviateClient, how_many: int) -> None:
    """Uses .aggregate behind-the-scenes"""
    name = "TestCollectionLength"
    client.collections.delete(name)
    collection = client.collections.create(
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    collection.data.insert_many([{"Name": f"name {i}"} for i in range(how_many)])
    assert len(collection) == how_many


def test_empty_aggregation(client: weaviate.WeaviateClient) -> None:
    name = "TestEmptyAggregation"
    client.collections.delete(name)
    collection = client.collections.create(
        name=name, properties=[Property(name="text", data_type=DataType.TEXT)]
    )
    res = collection.aggregate.over_all()
    assert res.total_count == 0


def test_simple_aggregation(client: weaviate.WeaviateClient) -> None:
    name = "TestSimpleAggregation"
    client.collections.delete(name)
    collection = client.collections.create(
        name=name, properties=[Property(name="text", data_type=DataType.TEXT)]
    )
    collection.data.insert({"text": "some text"})
    res = collection.aggregate.over_all(return_metrics=[Metrics("text").text(count=True)])
    assert isinstance(res.properties["text"], AggregateText)
    assert res.properties["text"].count == 1


def test_wrong_aggregation(client: weaviate.WeaviateClient) -> None:
    name = "TestEmptyAggregation"
    client.collections.delete(name)
    collection = client.collections.create(
        name=name, properties=[Property(name="text", data_type=DataType.TEXT)]
    )
    with pytest.raises(WeaviateQueryException) as e:
        collection.aggregate.over_all(total_count=False)
    assert (
        e.value.message
        == "The query that you sent had no body so GraphQL was unable to parse it. You must provide at least one option to the aggregation method in order to build a valid query."
    )


@pytest.mark.parametrize(
    "option,expected_len",
    [
        ({"object_limit": 1}, 1),
        ({"certainty": 0.9}, 1),
        ({"distance": 0.1}, 1),
        ({"object_limit": 2}, 2),
        ({"certainty": 0.1}, 2),
        ({"distance": 0.9}, 2),
    ],
)
def test_near_object_aggregation(
    client: weaviate.WeaviateClient, option: dict, expected_len: int
) -> None:
    name = "TestNearObjectAggregation"
    client.collections.delete(name)
    collection = client.collections.create(
        name=name,
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )
    text_1 = "some text"
    text_2 = "nothing like the other one at all, not even a little bit"
    uuid = collection.data.insert({"text": text_1})
    collection.data.insert({"text": text_2})
    res = collection.aggregate.near_object(
        uuid,
        return_metrics=[
            Metrics("text").text(count=True, top_occurrences_count=True, top_occurrences_value=True)
        ],
        **option,
    )
    assert isinstance(res.properties["text"], AggregateText)
    assert res.properties["text"].count == expected_len
    assert len(res.properties["text"].top_occurrences) == expected_len
    assert text_1 in [
        top_occurrence.value for top_occurrence in res.properties["text"].top_occurrences
    ]
    if expected_len == 2:
        assert text_2 in [
            top_occurrence.value for top_occurrence in res.properties["text"].top_occurrences
        ]
    else:
        assert text_2 not in [
            top_occurrence.value for top_occurrence in res.properties["text"].top_occurrences
        ]


def test_near_object_missing_param(client: weaviate.WeaviateClient) -> None:
    name = "TestNearVectorMissingParam"
    client.collections.delete(name)
    collection = client.collections.create(
        name=name,
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )
    text_1 = "some text"
    text_2 = "nothing like the other one at all, not even a little bit"
    uuid = collection.data.insert({"text": text_1})
    collection.data.insert({"text": text_2})
    with pytest.raises(WeaviateInvalidInputException) as e:
        collection.aggregate.near_object(
            uuid,
            return_metrics=[
                Metrics("text").text(
                    count=True, top_occurrences_count=True, top_occurrences_value=True
                )
            ],
        )
    assert (
        "You must provide at least one of the following arguments: certainty, distance, object_limit when vector searching"
        == e.value.message
    )


@pytest.mark.parametrize(
    "option,expected_len",
    [
        ({"object_limit": 1}, 1),
        ({"certainty": 0.9}, 1),
        ({"distance": 0.1}, 1),
        ({"object_limit": 2}, 2),
        ({"certainty": 0.1}, 2),
        ({"distance": 0.9}, 2),
    ],
)
def test_near_vector_aggregation(
    client: weaviate.WeaviateClient, option: dict, expected_len: int
) -> None:
    name = "TestNearVectorAggregation"
    client.collections.delete(name)
    collection = client.collections.create(
        name=name,
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )
    text_1 = "some text"
    text_2 = "nothing like the other one at all, not even a little bit"
    uuid = collection.data.insert({"text": text_1})
    obj = collection.query.fetch_object_by_id(uuid, include_vector=True)
    assert obj.vector is not None
    collection.data.insert({"text": text_2})
    res = collection.aggregate.near_vector(
        obj.vector,
        return_metrics=[
            Metrics("text").text(count=True, top_occurrences_count=True, top_occurrences_value=True)
        ],
        **option,
    )
    assert isinstance(res.properties["text"], AggregateText)
    assert res.properties["text"].count == expected_len
    assert len(res.properties["text"].top_occurrences) == expected_len
    assert text_1 in [
        top_occurrence.value for top_occurrence in res.properties["text"].top_occurrences
    ]
    if expected_len == 2:
        assert text_2 in [
            top_occurrence.value for top_occurrence in res.properties["text"].top_occurrences
        ]
    else:
        assert text_2 not in [
            top_occurrence.value for top_occurrence in res.properties["text"].top_occurrences
        ]


def test_near_vector_missing_param(client: weaviate.WeaviateClient) -> None:
    name = "TestNearVectorMissingParam"
    client.collections.delete(name)
    collection = client.collections.create(
        name=name,
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )
    uuid_ = collection.data.insert({"text": "some text"})
    obj = collection.query.fetch_object_by_id(uuid_, include_vector=True)
    assert obj.vector is not None
    with pytest.raises(WeaviateInvalidInputException) as e:
        collection.aggregate.near_vector(
            obj.vector,
            return_metrics=[
                Metrics("text").text(
                    count=True, top_occurrences_count=True, top_occurrences_value=True
                )
            ],
        )
    assert (
        "You must provide at least one of the following arguments: certainty, distance, object_limit when vector searching"
        == e.value.message
    )


@pytest.mark.parametrize(
    "option,expected_len",
    [
        ({"object_limit": 1}, 1),
        ({"certainty": 0.9}, 1),
        ({"distance": 0.1}, 1),
        ({"object_limit": 2}, 2),
        ({"certainty": 0.1}, 2),
        ({"distance": 0.9}, 2),
    ],
)
def test_near_text_aggregation(
    client: weaviate.WeaviateClient, option: dict, expected_len: int
) -> None:
    name = "TestNearTextAggregation"
    client.collections.delete(name)
    collection = client.collections.create(
        name=name,
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )
    text_1 = "some text"
    text_2 = "nothing like the other one at all, not even a little bit"
    collection.data.insert({"text": text_1})
    collection.data.insert({"text": text_2})
    res = collection.aggregate.near_text(
        text_1,
        return_metrics=[
            Metrics("text").text(count=True, top_occurrences_count=True, top_occurrences_value=True)
        ],
        **option,
    )
    assert isinstance(res.properties["text"], AggregateText)
    assert res.properties["text"].count == expected_len
    assert len(res.properties["text"].top_occurrences) == expected_len
    assert text_1 in [
        top_occurrence.value for top_occurrence in res.properties["text"].top_occurrences
    ]
    if expected_len == 2:
        assert text_2 in [
            top_occurrence.value for top_occurrence in res.properties["text"].top_occurrences
        ]
    else:
        assert text_2 not in [
            top_occurrence.value for top_occurrence in res.properties["text"].top_occurrences
        ]


def test_near_text_missing_param(client: weaviate.WeaviateClient) -> None:
    name = "TestNearTextMissingParam"
    client.collections.delete(name)
    collection = client.collections.create(
        name=name,
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )
    text_1 = "some text"
    collection.data.insert({"text": text_1})
    with pytest.raises(WeaviateInvalidInputException) as e:
        collection.aggregate.near_text(
            text_1,
            return_metrics=[
                Metrics("text").text(
                    count=True, top_occurrences_count=True, top_occurrences_value=True
                )
            ],
        )
    assert (
        "You must provide at least one of the following arguments: certainty, distance, object_limit when vector searching"
        == e.value.message
    )


@pytest.mark.parametrize("option", [{"object_limit": 1}, {"certainty": 0.9}, {"distance": 0.1}])
def test_near_image_aggregation(client: weaviate.WeaviateClient, option: dict) -> None:
    name = "TestNearImageAggregation"
    client.collections.delete(name)
    collection = client.collections.create(
        name=name,
        properties=[
            Property(name="rating", data_type=DataType.INT),
            Property(name="image", data_type=DataType.BLOB),
        ],
        vectorizer_config=Configure.Vectorizer.img2vec_neural(image_fields=["image"]),
    )
    img_path = pathlib.Path("integration/weaviate-logo.png")
    collection.data.insert({"image": file_encoder_b64(img_path), "rating": 9})
    res = collection.aggregate.near_image(
        img_path,
        return_metrics=[Metrics("rating").integer(count=True, maximum=True)],
        **option,
    )
    assert isinstance(res.properties["rating"], AggregateInteger)
    assert res.properties["rating"].count == 1
    assert res.properties["rating"].maximum == 9


def test_near_image_missing_param(client: weaviate.WeaviateClient) -> None:
    name = "TestNearImageMissingParam"
    client.collections.delete(name)
    collection = client.collections.create(
        name=name,
        properties=[
            Property(name="rating", data_type=DataType.INT),
            Property(name="image", data_type=DataType.BLOB),
        ],
        vectorizer_config=Configure.Vectorizer.img2vec_neural(image_fields=["image"]),
    )
    img_path = pathlib.Path("integration/weaviate-logo.png")
    collection.data.insert({"image": file_encoder_b64(img_path), "rating": 9})
    with pytest.raises(WeaviateInvalidInputException) as e:
        collection.aggregate.near_image(
            img_path,
            return_metrics=[
                Metrics("text").text(
                    count=True, top_occurrences_count=True, top_occurrences_value=True
                )
            ],
        )
    assert (
        "You must provide at least one of the following arguments: certainty, distance, object_limit when vector searching"
        == e.value.message
    )


def test_group_by_aggregation(client: weaviate.WeaviateClient) -> None:
    name = "TestGroupByAggregation"
    client.collections.delete(name)
    collection = client.collections.create(
        name=name,
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="int", data_type=DataType.INT),
        ],
    )
    collection.data.insert({"text": "some text", "int": 1})
    collection.data.insert({"text": "some text", "int": 2})

    res = collection.aggregate_group_by.over_all(
        "text",
        return_metrics=[
            Metrics("text").text(count=True),
            Metrics("int").integer(count=True),
        ],
    )
    assert len(res) == 1
    assert res[0].grouped_by.prop == "text"
    assert res[0].grouped_by.value == "some text"
    assert isinstance(res[0].properties["text"], AggregateText)
    assert res[0].properties["text"].count == 2
    assert isinstance(res[0].properties["int"], AggregateInteger)
    assert res[0].properties["int"].count == 2

    res = collection.aggregate_group_by.over_all(
        "int",
        return_metrics=[
            Metrics("text").text(count=True),
            Metrics("int").integer(count=True),
        ],
    )
    assert len(res) == 2
    assert res[0].grouped_by.prop == "int"
    assert res[0].grouped_by.value == "1" or res[1].grouped_by.value == "1"
    assert isinstance(res[0].properties["text"], AggregateText)
    assert res[0].properties["text"].count == 1
    assert isinstance(res[0].properties["int"], AggregateInteger)
    assert res[0].properties["int"].count == 1
    assert res[1].grouped_by.prop == "int"
    assert res[1].grouped_by.value == "2" or res[0].grouped_by.value == "2"
    assert isinstance(res[1].properties["text"], AggregateText)
    assert res[1].properties["text"].count == 1
    assert isinstance(res[1].properties["int"], AggregateInteger)
    assert res[1].properties["int"].count == 1


@pytest.mark.skip(reason="Validation logic is not robust enough currently")
def test_mistake_in_usage(client: weaviate.WeaviateClient) -> None:
    collection = client.collections.get("TestMistakeInUsage")
    with pytest.raises(TypeError) as e:
        collection.aggregate.over_all([Metrics("text")])  # type: ignore # testing incorrect usage
    assert (
        e.value.args[0]
        == "One of the aggregations is an unexpected type: <class 'weaviate.collection.classes.aggregate.Metrics'>. Did you forget to append a method call? E.g. .text(count=True)"
    )
    with pytest.raises(TypeError) as e:
        collection.aggregate.over_all(aggregations=[Metrics("text")])  # type: ignore # testing incorrect usage
    assert (
        e.value.args[0]
        == "One of the aggregations is an unexpected type: <class 'weaviate.collection.classes.aggregate.Metrics'>. Did you forget to append a method call?  E.g. .text(count=True)"
    )


def test_all_available_aggregations(client: weaviate.WeaviateClient) -> None:
    name = "TestAllAvailableAggregations"
    client.collections.delete(name)
    collection = client.collections.create(
        name=name,
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(
                name="texts",
                data_type=DataType.TEXT_ARRAY,
            ),
            Property(name="int", data_type=DataType.INT),
            Property(name="ints", data_type=DataType.INT_ARRAY),
            Property(name="float", data_type=DataType.NUMBER),
            Property(name="floats", data_type=DataType.NUMBER_ARRAY),
            Property(name="bool", data_type=DataType.BOOL),
            Property(name="bools", data_type=DataType.BOOL_ARRAY),
            Property(name="date", data_type=DataType.DATE),
            Property(name="dates", data_type=DataType.DATE_ARRAY),
        ],
        references=[
            ReferenceProperty(name="ref", target_collection="TestAllAvailableAggregations"),
        ],
    )
    collection.data.insert(
        {
            "text": "some text",
            "texts": ["some text", "some text"],
            "int": 1,
            "ints": [1, 2],
            "float": 1.0,
            "floats": [1.0, 2.0],
            "bool": True,
            "bools": [True, False],
            "date": "2021-01-01T00:00:00Z",
            "dates": ["2021-01-01T00:00:00Z", "2021-01-02T00:00:00Z"],
        }
    )
    res = collection.aggregate.over_all(
        return_metrics=[
            Metrics("text").text(
                count=True,
                top_occurrences_count=True,
                top_occurrences_value=True,
            ),
            Metrics("texts").text(
                count=True,
                top_occurrences_count=True,
                top_occurrences_value=True,
            ),
            Metrics("int").integer(
                count=True,
                maximum=True,
                mean=True,
                median=True,
                minimum=True,
                mode=True,
                sum_=True,
            ),
            Metrics("ints").integer(
                count=True,
                maximum=True,
                mean=True,
                median=True,
                minimum=True,
                mode=True,
                sum_=True,
            ),
            Metrics("float").number(
                count=True,
                maximum=True,
                mean=True,
                median=True,
                minimum=True,
                mode=True,
                sum_=True,
            ),
            Metrics("floats").number(
                count=True,
                maximum=True,
                mean=True,
                median=True,
                minimum=True,
                mode=True,
                sum_=True,
            ),
            Metrics("bool").boolean(
                count=True,
                percentage_false=True,
                percentage_true=True,
                total_false=True,
                total_true=True,
            ),
            Metrics("bools").boolean(
                count=True,
                percentage_false=True,
                percentage_true=True,
                total_false=True,
                total_true=True,
            ),
            Metrics("date").date_(
                count=True,
                maximum=True,
                median=True,
                minimum=True,
                mode=True,
            ),
            Metrics("dates").date_(
                count=True,
                maximum=True,
                median=True,
                minimum=True,
                mode=True,
            ),
        ]
    )

    text = res.properties["text"]
    assert isinstance(text, AggregateText)
    assert text.count == 1
    assert text.top_occurrences[0].count == 1
    assert text.top_occurrences[0].value == "some text"

    texts = res.properties["texts"]
    assert isinstance(texts, AggregateText)
    assert texts.count == 2
    assert texts.top_occurrences[0].count == 2
    assert texts.top_occurrences[0].value == "some text"

    int_ = res.properties["int"]
    assert isinstance(int_, AggregateInteger)
    assert int_.count == 1
    assert int_.maximum == 1
    assert int_.mean == 1
    assert int_.median == 1
    assert int_.minimum == 1
    assert int_.mode == 1
    assert int_.sum_ == 1

    ints = res.properties["ints"]
    assert isinstance(ints, AggregateInteger)
    assert ints.count == 2
    assert ints.maximum == 2
    assert ints.mean == 1.5
    assert ints.median == 1.5
    assert ints.minimum == 1
    assert ints.mode == 1

    float_ = res.properties["float"]
    assert isinstance(float_, AggregateNumber)
    assert float_.count == 1
    assert float_.maximum == 1.0
    assert float_.mean == 1.0
    assert float_.median == 1.0
    assert float_.minimum == 1.0
    assert float_.mode == 1.0

    floats = res.properties["floats"]
    assert isinstance(floats, AggregateNumber)
    assert floats.count == 2
    assert floats.maximum == 2.0
    assert floats.mean == 1.5
    assert floats.median == 1.5
    assert floats.minimum == 1.0
    assert floats.mode == 1.0

    bool_ = res.properties["bool"]
    assert isinstance(bool_, AggregateBoolean)
    assert bool_.count == 1
    assert bool_.percentage_false == 0
    assert bool_.percentage_true == 1
    assert bool_.total_false == 0
    assert bool_.total_true == 1

    bools = res.properties["bools"]
    assert isinstance(bools, AggregateBoolean)
    assert bools.count == 2
    assert bools.percentage_false == 0.5
    assert bools.percentage_true == 0.5
    assert bools.total_false == 1
    assert bools.total_true == 1

    date = res.properties["date"]
    assert isinstance(date, AggregateDate)
    assert date.count == 1
    assert date.maximum == "2021-01-01T00:00:00Z"
    assert date.median == "2021-01-01T00:00:00Z"
    assert date.minimum == "2021-01-01T00:00:00Z"
    assert date.mode == "2021-01-01T00:00:00Z"

    dates = res.properties["dates"]
    assert isinstance(dates, AggregateDate)
    assert dates.count == 2
    assert dates.maximum == "2021-01-02T00:00:00Z"
    assert dates.median == "2021-01-01T12:00:00Z"
    assert dates.minimum == "2021-01-01T00:00:00Z"
    # assert res.properties["dates"].mode == "2021-01-02T00:00:00Z" # flakey: sometimes return 01, other times 02
