from fastapi import APIRouter, Path, Query, HTTPException, Request, Body, Depends
from typing import List, Optional, Any
from urllib.parse import unquote
from models import (
    ObjectInstanceMinimal,
    ObjectInstance,
    HistoricalValue,
    ObjectType,
    UpdateResult,
    UpdateRequest,
    HistoricalUpdateResult,
    HistoricalValueUpdate,
    GetObjectsRequest,
    GetRelatedObjectsRequest,
    GetObjectValueRequest,
    GetObjectHistoryRequest,
)
from data_sources.data_interface import I3XDataSource
from datetime import datetime, timezone
from .utils import getValue, getObject

explore = APIRouter(prefix="", tags=["Explore"])
query = APIRouter(prefix="", tags=["Query"])
update = APIRouter(prefix="", tags=["Update"])

def get_data_source(request: Request) -> I3XDataSource:
    """Dependency to inject data source"""
    return request.app.state.data_source


# RFC 4.1.5 - Instances of an Object Type
@explore.get("/objects", summary="Get Objects", operation_id="getObjects")
def get_objects(
    typeId: Optional[str] = Query(default=None),
    includeMetadata: bool = Query(default=False),
    data_source: I3XDataSource = Depends(get_data_source),
) -> List[ObjectInstanceMinimal] | List[ObjectInstance]:
    """Return all Objects. Optionally filter by TypeId"""
    instances = [getObject(i, includeMetadata) for i in data_source.get_instances(typeId)]
    return instances
      

# RFC 4.1.5 - Query Objects by ElementId
@explore.post(
    "/objects/list",
    summary="List Objects by ElementId",
    operation_id="listObjectsById",
)
def query_objects_by_id(
    request_body: GetObjectsRequest,
    data_source: I3XDataSource = Depends(get_data_source),
):
    """
    Return one or more Objects by elementId.

    Request body: {"elementIds": ["...", "..."]}

    Returns array of objects.
    """
    element_ids = request_body.get_element_ids()
    results = []

    for eid in element_ids:
        instance = data_source.get_instance_by_id(eid)
        if instance:
            results.append(getObject(instance, request_body.includeMetadata))

    return results

# 4.1.6 Objects linked by Relationship Type
@explore.post(
    "/objects/related",
    summary="Query Related Objects",
    operation_id="queryRelatedObjects",
)
def query_related_objects(
    request_body: GetRelatedObjectsRequest,
    data_source: I3XDataSource = Depends(get_data_source),
):
    """
    Return related objects for one or more elementIds.

    Request body: {"elementIds": ["...", "..."]}

    Returns array of related objects.
    """
    element_ids = request_body.get_element_ids()
    results = []

    for eid in element_ids:
        eid_decoded = unquote(eid)
        instance = data_source.get_instance_by_id(eid_decoded)
        if instance:
            related_objects = data_source.get_related_instances(
                eid_decoded,
                request_body.relationshiptype
            )
            for obj in related_objects:
                results.append(getObject(obj, request_body.includeMetadata))

    return results


# RFC 4.2.1.1 - Object Element LastKnown Value
@query.post(
    "/objects/value",
    summary="Query Last Known Values",
    operation_id="queryLastKnownValues",
)
def query_last_known_values(
    request_body: GetObjectValueRequest,
    data_source: I3XDataSource = Depends(get_data_source),
):
    """
    Return last known value for one or more Objects.

    If maxDepth=0, recursively includes all values from HasComponent children (infinite depth).
    Otherwise, recurses only to the specified depth (1=no recursion, just this element).

    Request body: {"elementIds": ["...", "..."]}

    Returns array of values.
    """
    element_ids = request_body.get_element_ids()
    result = {}

    for eid in element_ids:
        eid_decoded = unquote(eid)
        instance = data_source.get_instance_by_id(eid_decoded)
        if instance:
            value = data_source.get_instance_values_by_id(
                eid_decoded,
                maxDepth=request_body.maxDepth,
                returnHistory=False
            )
            if value:
                # Merge into result (value is {elementId: {...}})
                result.update(value)

    return result

# 4.2.2.1 Object Element LastKnownValue
@update.put(
    "/objects/{elementId}/value",
    summary="Update Value of Object",
    operation_id="updateObjectValue",
)
def update_object(
    elementId: str = Path(...),
    body: Any = Body(...),  # Accept any JSON
    data_source: I3XDataSource = Depends(get_data_source),
):
    """Update the value of an Object"""
    # Call update_instance_value with a single-element list
    return data_source.update_instance_value(elementId, body)


# RFC 4.2.1.2 - Object Element HistoricalValue
@query.post(
    "/objects/history",
    response_model=Any,
    summary="Query Historical Values",
    operation_id="queryHistoricalValues",
)
def query_historical_values(
    request_body: GetObjectHistoryRequest,
    data_source: I3XDataSource = Depends(get_data_source),
):
    """
    Get the historical values for one or more Objects.

    If maxDepth=0, recursively includes all values from HasComponent children (infinite depth).
    Otherwise, recurses only to the specified depth (1=no recursion, just this element).

    Request body: {"elementIds": ["...", "..."]}

    Returns array of historical values.
    """
    element_ids = request_body.get_element_ids()
    result = {}

    for eid in element_ids:
        eid_decoded = unquote(eid)
        instance = data_source.get_instance_by_id(eid_decoded)
        if instance:
            historical_values = data_source.get_instance_values_by_id(
                eid_decoded,
                request_body.startTime,
                request_body.endTime,
                request_body.maxDepth,
                returnHistory=True
            )
            if historical_values:
                # Merge into result (value is {elementId: {...}})
                result.update(historical_values)

    return result

# RFC 4.2.2.2 - Object Element HistoricalValue
@update.put(
    "/objects/{elementId}/history",
    summary="Update Historical Values of Object",
    operation_id="updateObjectHistory",
)
def update_object_history(elementId: str = Path(...),data_source: I3XDataSource = Depends(get_data_source)):
    """Update the historical values for one or more Objects"""
    raise HTTPException(status_code=501, detail="Operation not implemented")
