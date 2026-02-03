from typing import Any
from datetime import datetime, timezone

def getObject(instance: Any, includeMetadata: bool) -> Any:
    """Helper to format object with or without metadata"""
    if includeMetadata:
        return instance

    noMetadataObject = {
        "elementId": instance["elementId"],
        "displayName": instance["displayName"],
        "typeId": instance["typeId"],
        "namespaceUri": instance["namespaceUri"],
        "parentId": instance.get("parentId"),
        "isComposition": instance["isComposition"]
    }
    return noMetadataObject
    
def getValue(value: Any, includeMetadata: bool) -> Any:
    """Helper to format value with or without metadata"""
    if not includeMetadata:
        return value

    metadataValue = {
        "dataType": "object",
        "quality": "GoodNoData" if not value else "Good",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "value": value
    }

    return metadataValue

def getValueMetadata(value: Any) -> Any:
    """Helper to extract metadata from value"""
    metadata = {
        "dataType": "object",
        "quality": "GoodNoData" if not value else "Good",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return metadata

def getSubscriptionValue(instance: Any, record: Any, maxDepth: int = 1, data_source: Any = None) -> Any:
    """
    Helper to get subscription value, optionally with recursive HasComponent children.

    Args:
        instance: The instance object with elementId
        record: The record object with structure {value: ..., quality: ..., timestamp: ..., etc}
        maxDepth: Controls recursion (0=infinite, 1=no recursion, N=recurse N levels). Requires data_source if not 1.
        data_source: Data source to fetch recursive values (required if maxDepth != 1)

    Returns:
        Dictionary with format: {elementId: {data: [VQT], ...children}}
    """
    element_id = instance["elementId"]

    # If maxDepth != 1 (i.e., recursion is needed) and we have a data_source, fetch the full recursive structure
    should_recurse = (maxDepth == 0 or maxDepth > 1)
    if should_recurse and data_source is not None:
        # Use the data source to get the full recursive value structure
        return data_source.get_instance_values_by_id(
            element_id,
            maxDepth=maxDepth,
            returnHistory=False
        )

    # Build VQT object
    actual_value = record.get("value") if isinstance(record, dict) else record
    vqt = {"value": actual_value}

    # Include all record-level metadata fields (quality, timestamp, etc.)
    if isinstance(record, dict):
        for key, val in record.items():
            if key != "value":
                vqt[key] = val

    # Return in new format: {elementId: {data: [VQT]}}
    return {element_id: {"data": [vqt]}}


    
