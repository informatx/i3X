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
@explore.get("/objects", summary="Get Objects")
def get_objects(
    typeId: Optional[str] = Query(default=None),
    includeMetadata: bool = Query(default=False),
    data_source: I3XDataSource = Depends(get_data_source),
) -> List[ObjectInstanceMinimal] | List[ObjectInstance]:
    """Return all Objects. Optionally filter by TypeId"""
    instances = [getObject(i, includeMetadata) for i in data_source.get_instances(typeId)]
    return instances
      

# RFC 4.1.5 - Query Objects by ElementId
@explore.post("/objects/list", summary="List Objects by ElementId")
def query_objects_by_id(
    request_body: GetObjectsRequest,
    data_source: I3XDataSource = Depends(get_data_source),
):
    """
    Return one or more Objects by elementId.

    Request body: {"elementIds": ["...", "..."]}

    Returns array of results, each with success/failure status.
    """
    element_ids = request_body.get_element_ids()
    results = []

    for eid in element_ids:
        instance = data_source.get_instance_by_id(eid)
        if instance:
            results.append({
                "elementId": eid,
                "success": True,
                "data": getObject(instance, request_body.includeMetadata)
            })
        else:
            results.append({
                "elementId": eid,
                "success": False,
                "error": f"Instance with elementId '{eid}' not found"
            })

    return {
        "results": results,
        "totalRequested": len(element_ids),
        "totalSuccess": sum(1 for r in results if r["success"]),
        "totalFailed": sum(1 for r in results if not r["success"])
    }

# 4.1.6 Objects linked by Relationship Type
@explore.post("/objects/related", summary="Query Related Objects")
def query_related_objects(
    request_body: GetRelatedObjectsRequest,
    data_source: I3XDataSource = Depends(get_data_source),
):
    """
    Return related objects for one or more elementIds.

    Request body: {"elementIds": ["...", "..."]}

    Returns array of results, each with success/failure status.
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
            results.append({
                "elementId": eid,
                "success": True,
                "data": [getObject(obj, request_body.includeMetadata) for obj in related_objects]
            })
        else:
            results.append({
                "elementId": eid,
                "success": False,
                "error": f"Instance with elementId '{eid}' not found"
            })

    return {
        "results": results,
        "totalRequested": len(element_ids),
        "totalSuccess": sum(1 for r in results if r["success"]),
        "totalFailed": sum(1 for r in results if not r["success"])
    }


# RFC 4.2.1.1 - Object Element LastKnown Value
@query.post("/objects/value", summary="Query Last Known Values")
def query_last_known_values(
    request_body: GetObjectValueRequest,
    data_source: I3XDataSource = Depends(get_data_source),
):
    """
    Return last known value for one or more Objects.

    If maxDepth=0, recursively includes all values from HasComponent children (infinite depth).
    Otherwise, recurses only to the specified depth (1=no recursion, just this element).

    Request body: {"elementIds": ["...", "..."]}

    Returns array of results, each with success/failure status.
    """
    element_ids = request_body.get_element_ids()
    results = []

    for eid in element_ids:
        eid_decoded = unquote(eid)
        instance = data_source.get_instance_by_id(eid_decoded)
        if instance:
            value = data_source.get_instance_values_by_id(
                eid_decoded,
                maxDepth=request_body.maxDepth,
                returnHistory=False
            )
            results.append({
                "elementId": eid,
                "success": True,
                "data": {
                    "elementId": eid,
                    "isComposition": instance.get("isComposition", False),
                    "value": value
                }
            })
        else:
            results.append({
                "elementId": eid,
                "success": False,
                "error": f"Element '{eid}' not found"
            })

    return {
        "results": results,
        "totalRequested": len(element_ids),
        "totalSuccess": sum(1 for r in results if r["success"]),
        "totalFailed": sum(1 for r in results if not r["success"])
    }

# 4.2.2.1 Object Element LastKnownValue
@update.put("/objects/{elementId}/value", summary="Update Value of Object")
def update_object(
    elementId: str = Path(...),
    body: Any = Body(...),  # Accept any JSON
    data_source: I3XDataSource = Depends(get_data_source),
):
    """Update the value of an Object"""
    # Call update_instance_value with a single-element list
    return data_source.update_instance_value(elementId, body)


# RFC 4.2.1.2 - Object Element HistoricalValue
@query.post("/objects/history", response_model=Any, summary="Query Historical Values")
def query_historical_values(
    request_body: GetObjectHistoryRequest,
    data_source: I3XDataSource = Depends(get_data_source),
):
    """
    Get the historical values for one or more Objects.

    If maxDepth=0, recursively includes all values from HasComponent children (infinite depth).
    Otherwise, recurses only to the specified depth (1=no recursion, just this element).

    Request body: {"elementIds": ["...", "..."]}

    Returns array of results, each with success/failure status.
    """
    element_ids = request_body.get_element_ids()
    results = []

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
            results.append({
                "elementId": eid,
                "success": True,
                "data": historical_values
            })
        else:
            results.append({
                "elementId": eid,
                "success": False,
                "error": f"Element '{eid}' not found"
            })

    return {
        "results": results,
        "totalRequested": len(element_ids),
        "totalSuccess": sum(1 for r in results if r["success"]),
        "totalFailed": sum(1 for r in results if not r["success"])
    }

# RFC 4.2.2.2 - Object Element HistoricalValue
@update.put("/objects/{elementId}/history", summary="Update Historical Values of Object")
def update_object_history(elementId: str = Path(...),data_source: I3XDataSource = Depends(get_data_source)):
    """Update the historical values for one or more Objects"""
    raise HTTPException(status_code=501, detail="Operation not implemented")
