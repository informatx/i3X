from fastapi import APIRouter, Path, Query, HTTPException, Request, Depends
from typing import List, Optional
from urllib.parse import unquote
from models import ObjectType, RelationshipType, GetObjectTypesRequest, GetRelationshipTypesRequest
from data_sources.data_interface import I3XDataSource

typeDefinitions = APIRouter(prefix="", tags=["Explore"])


def get_data_source(request: Request) -> I3XDataSource:
    """Dependency to inject data source"""
    return request.app.state.data_source

# RFC 4.1.3 - Object Types
@typeDefinitions.get(
    "/objecttypes", response_model=List[ObjectType], summary="Get Object Types"
)
def get_object_types(
    namespaceUri: Optional[str] = Query(default=None),
    data_source: I3XDataSource = Depends(get_data_source),
):
    """Get the schemas for all Types. Optionally filter by Namespace"""
    return data_source.get_object_types(namespaceUri)

# RFC 4.1.2 - Object Type Definition
@typeDefinitions.post("/objecttypes/query", summary="Query Object Types by ElementId")
def query_object_types_by_id(
    request_body: GetObjectTypesRequest,
    data_source: I3XDataSource = Depends(get_data_source),
):
    """
    Get the schema for one or more Types by ElementID.

    Accepts either:
    - {"elementId": "..."} for single type
    - {"elementIds": ["...", "..."]} for multiple types

    Returns array of results, each with success/failure status.
    """
    element_ids = request_body.get_element_ids()
    results = []

    for eid in element_ids:
        eid_decoded = unquote(eid)
        obj_type = data_source.get_object_type_by_id(eid_decoded)
        if obj_type:
            results.append({
                "elementId": eid,
                "success": True,
                "data": obj_type
            })
        else:
            results.append({
                "elementId": eid,
                "success": False,
                "error": f"Object type '{eid}' not found"
            })

    return {
        "results": results,
        "totalRequested": len(element_ids),
        "totalSuccess": sum(1 for r in results if r["success"]),
        "totalFailed": sum(1 for r in results if not r["success"])
    }


# RFC 4.1.4 - Relationship Types
@typeDefinitions.get(
    "/relationshiptypes", response_model=List[RelationshipType], summary="Get Relationship Types"
)
def get_relationship_types(
    namespaceUri: Optional[str] = Query(default=None),
    data_source: I3XDataSource = Depends(get_data_source),
):
    """Get all Relationship Types. Optionally filtered by Namespace"""
    relationship_types = data_source.get_relationship_types()

    if namespaceUri:
        return [
            rt for rt in relationship_types if rt.get("namespaceUri") == namespaceUri
        ]

    return relationship_types

# RFC 4.1.4 - Relationship Type
@typeDefinitions.post("/relationshiptypes/query", summary="Query Relationship Types by ElementId")
def query_relationship_types_by_id(
    request_body: GetRelationshipTypesRequest,
    data_source: I3XDataSource = Depends(get_data_source),
):
    """
    Get one or more Relationship Types by ElementID.

    Accepts either:
    - {"elementId": "..."} for single type
    - {"elementIds": ["...", "..."]} for multiple types

    Returns array of results, each with success/failure status.
    """
    element_ids = request_body.get_element_ids()
    results = []

    for eid in element_ids:
        eid_decoded = unquote(eid)
        rel_type = data_source.get_relationship_type_by_id(eid_decoded)
        if rel_type:
            results.append({
                "elementId": eid,
                "success": True,
                "data": rel_type
            })
        else:
            results.append({
                "elementId": eid,
                "success": False,
                "error": f"Relationship type '{eid}' not found"
            })

    return {
        "results": results,
        "totalRequested": len(element_ids),
        "totalSuccess": sum(1 for r in results if r["success"]),
        "totalFailed": sum(1 for r in results if not r["success"])
    }
