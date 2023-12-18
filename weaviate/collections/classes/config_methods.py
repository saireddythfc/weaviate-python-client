from typing import Any, Dict, List, Optional, Union, cast

from weaviate.collections.classes.config import (
    _BQConfig,
    _CollectionConfig,
    _CollectionConfigSimple,
    _PQConfig,
    _VectorIndexConfigFlat,
    _InvertedIndexConfig,
    _BM25Config,
    _StopwordsConfig,
    _MultiTenancyConfig,
    _Property,
    _ReferenceProperty,
    _ReplicationConfig,
    _ShardingConfig,
    _VectorIndexConfigHNSW,
    StopwordsPreset,
    VectorDistance,
    PQEncoderType,
    PQEncoderDistribution,
    _VectorIndexType,
    Vectorizer,
    Tokenization,
    _PQEncoderConfig,
    _PropertyVectorizerConfig,
    _VectorizerConfig,
    _GenerativeConfig,
    GenerativeSearches,
    DataType,
)


def _is_primitive(d_type: str) -> bool:
    return d_type[0][0].lower() == d_type[0][0]


def _collection_config_simple_from_json(schema: Dict[str, Any]) -> _CollectionConfigSimple:
    if schema["vectorizer"] != "none":
        vec_config: Optional[Dict[str, Any]] = schema["moduleConfig"].pop(
            schema["vectorizer"], None
        )
        assert vec_config is not None
        vectorizer_config = _VectorizerConfig(
            vectorize_collection_name=vec_config.pop("vectorizeClassName", False),
            model=vec_config,
        )
    else:
        vectorizer_config = None

    if len(generators := list(schema.get("moduleConfig", {}).keys())) == 1:
        generative_config = _GenerativeConfig(
            generator=GenerativeSearches(generators[0]),
            model=schema["moduleConfig"][generators[0]],
        )
    else:
        generative_config = None

    return _CollectionConfigSimple(
        name=schema["class"],
        description=schema.get("description"),
        generative_config=generative_config,
        properties=_properties_from_config(schema) if schema.get("properties") is not None else [],
        references=_references_from_config(schema) if schema.get("properties") is not None else [],
        vectorizer_config=vectorizer_config,
        vectorizer=Vectorizer(schema["vectorizer"]),
    )


def _collection_config_from_json(schema: Dict[str, Any]) -> _CollectionConfig:
    if schema["vectorizer"] != "none":
        vec_config: Optional[Dict[str, Any]] = schema["moduleConfig"].pop(
            schema["vectorizer"], None
        )
        assert vec_config is not None
        vectorizer_config = _VectorizerConfig(
            vectorize_collection_name=vec_config.pop("vectorizeClassName", False),
            model=vec_config,
        )
    else:
        vectorizer_config = None

    if len(generators := list(schema.get("moduleConfig", {}).keys())) == 1:
        generative_config = _GenerativeConfig(
            generator=GenerativeSearches(generators[0]),
            model=schema["moduleConfig"][generators[0]],
        )
    else:
        generative_config = None

    quantitizer: Optional[Union[_PQConfig, _BQConfig]] = None
    if "bq" in schema["vectorIndexConfig"] and schema["vectorIndexConfig"]["bq"]["enabled"]:
        quantitizer = _BQConfig(
            cache=schema["vectorIndexConfig"]["bq"]["cache"],
            rescore_limit=schema["vectorIndexConfig"]["bq"]["rescoreLimit"],
        )
    elif "pq" in schema["vectorIndexConfig"] and schema["vectorIndexConfig"]["pq"]["enabled"]:
        quantitizer = _PQConfig(
            bit_compression=schema["vectorIndexConfig"]["pq"]["bitCompression"],
            segments=schema["vectorIndexConfig"]["pq"]["segments"],
            centroids=schema["vectorIndexConfig"]["pq"]["centroids"],
            training_limit=schema["vectorIndexConfig"]["pq"]["trainingLimit"],
            encoder=_PQEncoderConfig(
                type_=PQEncoderType(schema["vectorIndexConfig"]["pq"]["encoder"]["type"]),
                distribution=PQEncoderDistribution(
                    schema["vectorIndexConfig"]["pq"]["encoder"]["distribution"]
                ),
            ),
        )

    if schema["vectorIndexType"] == "hnsw":
        vector_index_config: Union[
            _VectorIndexConfigHNSW, _VectorIndexConfigFlat
        ] = _VectorIndexConfigHNSW(
            cleanup_interval_seconds=schema["vectorIndexConfig"]["cleanupIntervalSeconds"],
            distance_metric=VectorDistance(schema["vectorIndexConfig"]["distance"]),
            dynamic_ef_min=schema["vectorIndexConfig"]["dynamicEfMin"],
            dynamic_ef_max=schema["vectorIndexConfig"]["dynamicEfMax"],
            dynamic_ef_factor=schema["vectorIndexConfig"]["dynamicEfFactor"],
            ef=schema["vectorIndexConfig"]["ef"],
            ef_construction=schema["vectorIndexConfig"]["efConstruction"],
            flat_search_cutoff=schema["vectorIndexConfig"]["flatSearchCutoff"],
            max_connections=schema["vectorIndexConfig"]["maxConnections"],
            quantitizer=quantitizer,
            skip=schema["vectorIndexConfig"]["skip"],
            vector_cache_max_objects=schema["vectorIndexConfig"]["vectorCacheMaxObjects"],
        )
    else:
        assert schema["vectorIndexType"] == "flat"
        vector_index_config = _VectorIndexConfigFlat(
            distance_metric=VectorDistance(schema["vectorIndexConfig"]["distance"]),
            quantitizer=quantitizer,
            vector_cache_max_objects=schema["vectorIndexConfig"]["vectorCacheMaxObjects"],
        )
    return _CollectionConfig(
        name=schema["class"],
        description=schema.get("description"),
        generative_config=generative_config,
        inverted_index_config=_InvertedIndexConfig(
            bm25=_BM25Config(
                b=schema["invertedIndexConfig"]["bm25"]["b"],
                k1=schema["invertedIndexConfig"]["bm25"]["k1"],
            ),
            cleanup_interval_seconds=schema["invertedIndexConfig"]["cleanupIntervalSeconds"],
            index_null_state=cast(dict, schema["invertedIndexConfig"]).get("indexNullState")
            is True,
            index_property_length=cast(dict, schema["invertedIndexConfig"]).get(
                "indexPropertyLength"
            )
            is True,
            index_timestamps=cast(dict, schema["invertedIndexConfig"]).get("indexTimestamps")
            is True,
            stopwords=_StopwordsConfig(
                preset=StopwordsPreset(schema["invertedIndexConfig"]["stopwords"]["preset"]),
                additions=schema["invertedIndexConfig"]["stopwords"]["additions"],
                removals=schema["invertedIndexConfig"]["stopwords"]["removals"],
            ),
        ),
        multi_tenancy_config=_MultiTenancyConfig(enabled=schema["multiTenancyConfig"]["enabled"]),
        properties=_properties_from_config(schema) if schema.get("properties") is not None else [],
        references=_references_from_config(schema) if schema.get("properties") is not None else [],
        replication_config=_ReplicationConfig(factor=schema["replicationConfig"]["factor"]),
        sharding_config=_ShardingConfig(
            virtual_per_physical=schema["shardingConfig"]["virtualPerPhysical"],
            desired_count=schema["shardingConfig"]["desiredCount"],
            actual_count=schema["shardingConfig"]["actualCount"],
            desired_virtual_count=schema["shardingConfig"]["desiredVirtualCount"],
            actual_virtual_count=schema["shardingConfig"]["actualVirtualCount"],
            key=schema["shardingConfig"]["key"],
            strategy=schema["shardingConfig"]["strategy"],
            function=schema["shardingConfig"]["function"],
        ),
        vector_index_config=vector_index_config,
        vector_index_type=_VectorIndexType(schema["vectorIndexType"]),
        vectorizer_config=vectorizer_config,
        vectorizer=Vectorizer(schema["vectorizer"]),
    )


def _collection_configs_from_json(schema: Dict[str, Any]) -> Dict[str, _CollectionConfig]:
    return {schema["class"]: _collection_config_from_json(schema) for schema in schema["classes"]}


def _collection_configs_simple_from_json(
    schema: Dict[str, Any]
) -> Dict[str, _CollectionConfigSimple]:
    return {
        schema["class"]: _collection_config_simple_from_json(schema) for schema in schema["classes"]
    }


def _properties_from_config(schema: Dict[str, Any]) -> List[_Property]:
    props: List[_Property] = []
    for prop in schema["properties"]:
        if not _is_primitive(prop["dataType"]):
            continue
        props.append(
            _Property(
                data_type=DataType(prop["dataType"][0]),
                description=prop.get("description"),
                index_filterable=prop["indexFilterable"],
                index_searchable=prop["indexSearchable"],
                name=prop["name"],
                tokenization=Tokenization(prop["tokenization"])
                if prop.get("tokenization") is not None
                else None,
                vectorizer_config=_PropertyVectorizerConfig(
                    skip=prop["moduleConfig"][schema["vectorizer"]]["skip"],
                    vectorize_property_name=prop["moduleConfig"][schema["vectorizer"]][
                        "vectorizePropertyName"
                    ],
                )
                if schema["vectorizer"] != "none"
                else None,
                vectorizer=schema["vectorizer"],
            )
        )
    return props


def _references_from_config(schema: Dict[str, Any]) -> List[_ReferenceProperty]:
    refs: List[_ReferenceProperty] = []
    for prop in schema["properties"]:
        if _is_primitive(prop["dataType"]):
            continue
        refs.append(
            _ReferenceProperty(
                target_collections=prop["dataType"],
                description=prop.get("description"),
                index_filterable=prop["indexFilterable"],
                index_searchable=prop["indexSearchable"],
                name=prop["name"],
                tokenization=Tokenization(prop["tokenization"])
                if prop.get("tokenization") is not None
                else None,
                vectorizer_config=_PropertyVectorizerConfig(
                    skip=prop["moduleConfig"][schema["vectorizer"]]["skip"],
                    vectorize_property_name=prop["moduleConfig"][schema["vectorizer"]][
                        "vectorizePropertyName"
                    ],
                )
                if schema["vectorizer"] != "none"
                else None,
                vectorizer=schema["vectorizer"],
            )
        )
    return refs