from typing import Generic, List, Optional

from weaviate.collections.classes.filters import (
    _Filters,
)
from weaviate.collections.classes.grpc import GroupBy, Rerank, METADATA
from weaviate.collections.classes.internal import (
    QuerySearchReturnType,
    ReturnProperties,
    ReturnReferences,
)
from weaviate.collections.classes.types import Properties, TProperties, References, TReferences
from weaviate.collections.queries.base_sync import _BaseQuery
from weaviate.types import INCLUDE_VECTOR


class _BM25Query(Generic[Properties, References], _BaseQuery[Properties, References]):
    def bm25(
        self,
        query: Optional[str],
        *,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[GroupBy] = None,
        rerank: Optional[Rerank] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None,
    ) -> QuerySearchReturnType[Properties, References, TProperties, TReferences]:
        """Search for objects in this collection using the keyword-based BM25 algorithm.

        See the [docs](https://weaviate.io/developers/weaviate/search/bm25) for a more detailed explanation.

        Arguments:
            `query`
                The keyword-based query to search for, REQUIRED. If None, a normal search will be performed.
            `query_properties`
                The properties to search in. If not specified, all properties are searched.
            `limit`
                The maximum number of results to return. If not specified, the default limit specified by the server is returned.
            `offset`
                The offset to start from. If not specified, the retrieval begins from the first object in the server.
            `auto_limit`
                The maximum number of [autocut](https://weaviate.io/developers/weaviate/api/graphql/additional-operators#autocut) results to return. If not specified, no limit is applied.
            `filters`
                The filters to apply to the search.
            `group_by`
                How the results should be grouped by a specific property.
            `rerank`
                How the results should be reranked. NOTE: A `rerank-*` module must be enabled for this functionality to work.
            `include_vector`
                Whether to include the vector in the results. If not specified, this is set to False.
            `return_metadata`
                The metadata to return for each object, defaults to `None`.
            `return_properties`
                The properties to return for each object.

        NOTE:
            If `return_properties` is not provided then all non-reference properties are returned including nested properties.
            If `return_metadata` is not provided then no metadata is provided. Use MetadataQuery.full() to retrieve all metadata.
            If `return_references` is not provided then no references are provided.

        Returns:
            A `QueryReturn` object that includes the searched objects.

        Raises:
            `weaviate.exceptions.WeaviateGRPCQueryError`:
                If the network connection to Weaviate fails.
        """
        return self._loop.run_until_complete(
            self._query.bm25,
            query=query,
            query_properties=query_properties,
            limit=limit,
            offset=offset,
            auto_limit=auto_limit,
            filters=filters,
            group_by=group_by,
            rerank=rerank,
            include_vector=include_vector,
            return_metadata=return_metadata,
            return_properties=return_properties,
            return_references=return_references,
        )
