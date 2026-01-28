# I3X Implementation Guide

This document provides comprehensive guidance for implementing RFC 001-compliant I3X (Industrial Information Interface eXchange) servers. It supplements the OpenAPI specification (`openapi.yaml`) with behavioral requirements, edge cases, and architecture recommendations.

## Table of Contents

1. [Introduction](#1-introduction)
2. [Core Concepts](#2-core-concepts)
3. [Data Model Requirements](#3-data-model-requirements)
4. [API Implementation](#4-api-implementation)
5. [Subscription System](#5-subscription-system)
6. [Architecture Recommendations](#6-architecture-recommendations)
7. [Security](#7-security)
8. [Compliance Testing](#8-compliance-testing)

---

## 1. Introduction

### 1.1 Purpose and Scope

This guide enables developers to build RFC 001-compliant I3X servers in any programming language. It covers:

- **Normative requirements**: Behaviors that MUST be implemented for compliance
- **Optional features**: Behaviors that MAY be implemented to enhance functionality
- **Architecture recommendations**: Suggested patterns for robust implementations

### 1.2 Relationship to RFC 001

This guide is derived from RFC 001 "Common API for Industrial Information Interface eXchange (I3X)". Where this guide and the RFC differ, the RFC takes precedence. This guide provides additional implementation detail not specified in the RFC.

### 1.3 Compliance Levels

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" are interpreted as described in Internet RFC 2119.

**Compliance Levels:**

| Level | Description |
|-------|-------------|
| **Core** | All exploratory methods (RFC 4.1.x) and current value queries (RFC 4.2.1.1) |
| **Extended** | Core + historical values (RFC 4.2.1.2) and subscriptions (RFC 4.2.3.x) |
| **Full** | Extended + value updates (RFC 4.2.2.x) |

Implementations MUST support Core level. Extended and Full levels are RECOMMENDED for production deployments.

---

## 2. Core Concepts

### 2.1 ElementId Format and Uniqueness

**Definition:** An ElementId is a platform-specific, persistent, unique string identifier for any element in the address space.

**Requirements:**

- ElementIds MUST be strings
- ElementIds MUST be unique within the scope of the platform
- ElementIds MUST be persistent (the same element always has the same ID)
- ElementIds MUST be URL-safe or properly encoded when used in paths
- ElementIds SHOULD be human-readable when practical

**Examples of valid ElementIds:**
```
machine-001
sensor_temperature_01
urn:example:equipment:pump:123
MachineType
HasParent
```

**URL Encoding:**

When an ElementId contains characters not allowed in URLs (e.g., `/`, `#`, `?`), it MUST be percent-encoded:

```
Original:    equipment/pump#123
Encoded:     equipment%2Fpump%23123
```

Servers MUST decode percent-encoded ElementIds in path parameters.

### 2.2 Namespace Semantics

**Definition:** A Namespace provides a logical scope within the address space that groups related types, instances, and relationships.

**Requirements:**

- Each Namespace MUST have a unique URI
- Each Namespace MUST have a displayName
- All Object Types MUST belong to exactly one Namespace
- All Object Instances MUST belong to exactly one Namespace
- Relationship Types SHOULD belong to a Namespace

**Standard Namespace URIs:**

Implementations MAY define their own namespace URIs. Recommended patterns:

```
https://www.company.com/ns/equipment
https://www.isa.org/isa95
urn:i3x:relationships
```

### 2.3 Object Type vs Instance Relationship

**Object Types** define the schema (structure, attributes) for a class of objects. They are analogous to classes in object-oriented programming.

**Object Instances** are actual equipment, sensors, or processes with current attribute values. They are derived from Object Types.

**Requirements:**

- Every Object Instance MUST reference its Object Type via `typeId`
- The `typeId` MUST correspond to an existing Object Type's `elementId`
- Object Instances MUST conform to their Object Type's schema

**Example:**

```json
// Object Type
{
  "elementId": "TemperatureSensorType",
  "displayName": "Temperature Sensor",
  "namespaceUri": "https://example.com/ns/sensors",
  "schema": {
    "type": "object",
    "properties": {
      "temperature": { "type": "number" },
      "unit": { "type": "string", "enum": ["C", "F", "K"] }
    }
  }
}

// Object Instance (derived from above type)
{
  "elementId": "temp-sensor-001",
  "displayName": "Reactor Temperature Sensor",
  "typeId": "TemperatureSensorType",
  "namespaceUri": "https://example.com/ns/sensors",
  "parentId": "reactor-001",
  "isComposition": false
}
```

### 2.4 VQT (Value-Quality-Timestamp) Format

All value responses MUST include the VQT structure:

```json
{
  "value": <any>,
  "quality": "Good" | "GoodNoData" | "Bad" | "Uncertain",
  "timestamp": "2025-01-08T10:30:00Z"
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `value` | any | Yes | The actual data value (any JSON type) |
| `quality` | string | Yes | Data quality indicator |
| `timestamp` | string | Yes | RFC 3339 timestamp when data was recorded |

### 2.5 Quality Values

| Quality | Description | When to Use |
|---------|-------------|-------------|
| `Good` | Value is valid and current | Normal operation, value is reliable |
| `GoodNoData` | No data available but connection is good | Sensor connected but hasn't reported yet |
| `Bad` | Value is invalid or connection failed | Communication failure, sensor malfunction |
| `Uncertain` | Value quality cannot be determined | Sensor in calibration, stale data |

**Quality Determination Rules:**

1. If the value was received within the expected update interval: `Good`
2. If the element exists but has no recorded values: `GoodNoData`
3. If the data source reports an error or timeout: `Bad`
4. If the value age exceeds a threshold but connection is alive: `Uncertain`

---

## 3. Data Model Requirements

### 3.1 Required Object Metadata Fields

Every Object Instance response MUST include these fields (RFC 3.1.1):

| Field | Type | Description |
|-------|------|-------------|
| `elementId` | string | Unique identifier |
| `displayName` | string | Human-friendly name |
| `typeId` | string | ElementId of the Object Type |
| `parentId` | string? | ElementId of parent (null if root) |
| `isComposition` | boolean | True if the element encapsulates its children |
| `namespaceUri` | string | Namespace URI |

### 3.2 Optional Object Metadata Fields

When `includeMetadata=true`, implementations MAY include (RFC 3.1.2):

| Field | Type | Description |
|-------|------|-------------|
| `interpolation` | string | Interpolation method if value is interpolated |
| `engUnit` | string | Engineering unit (UNECE Rec 20 format) |
| `quality` | string | Current data quality |
| `relationships` | object | Relationship map |

### 3.3 Relationship Type Semantics

#### 3.3.1 Organizational Relationships (Required)

**HasParent / HasChildren**

These represent topological or organizational hierarchy where child objects are separate entities organized under a parent.

```
Production Line A (parent)
├── Machine 1 (child)
├── Machine 2 (child)
└── Machine 3 (child)
```

**Requirements:**

- If object A `HasParent` B, then B `HasChildren` A
- `parentId` on instances MUST match the `HasParent` relationship
- Traversing `HasChildren` returns distinct, independently-valued objects

#### 3.3.2 Composition Relationships (Optional)

**HasComponent / ComponentOf**

These indicate when child data IS *part of* the parent's definition -- that is, the child's members are encapsulated within the parent's.

**Note:** isComposition is NEVER used to indicate ownership or hierarchy. It is strictly used to indicate how the data model is constructed. When isComposition is TRUE, the parent's value is composed of its children's values.

```
CNC Machine (parent, isComposition: true)
├── Spindle (component)
├── Coolant System (component)
└── Control Panel (component)
```

**Requirements:**

- If object A `HasComponent` B, then B `ComponentOf` A
- Parent MUST have `isComposition: true`
- Querying parent value with `maxDepth > 1` returns nested child values
- Component children's values are part of the parent's logical value

### 3.4 maxDepth Parameter Semantics

The `maxDepth` parameter controls recursion through HasComponent relationships:

| Value | Behavior |
|-------|----------|
| `0` | Infinite recursion - include all nested composed elements |
| `1` | No recursion - return only this element's direct value (default) |
| `N` | Recurse up to N levels deep through HasComponent relationships |

**Response Structure with maxDepth:**

When `maxDepth > 1` and the element has components:

```json
{
  "elementId": "machine-001",
  "isComposition": true,
  "value": {
    "_value": {
      "value": { "status": "running" },
      "quality": "Good",
      "timestamp": "2025-01-08T10:30:00Z"
    },
    "spindle-001": {
      "value": { "rpm": 12000 },
      "quality": "Good",
      "timestamp": "2025-01-08T10:30:00Z"
    },
    "coolant-001": {
      "value": { "flow_rate": 5.2, "temp": 22.1 },
      "quality": "Good",
      "timestamp": "2025-01-08T10:30:00Z"
    }
  }
}
```

**Key Points:**

- `_value` contains the parent element's own value
- Child component values are keyed by their `elementId`
- Each child value is in VQT format
- Recursion only follows `HasComponent` relationships, not `HasChildren`

---

## 4. API Implementation

### 4.1 Request/Response Formats

**JSON Required:**

- Implementations MUST support JSON for all requests and responses
- `Content-Type: application/json` SHOULD be the default
- Implementations MAY support additional formats (e.g., binary) per RFC 5.1.1

**Request Headers:**

```
Content-Type: application/json
Accept: application/json
X-API-Key: <api-key>  (or Authorization: Bearer <token>)
```

### 4.2 Error Handling

**HTTP Status Codes:**

| Code | Meaning | When to Use |
|------|---------|-------------|
| 200 | OK | Successful request |
| 400 | Bad Request | Invalid parameters, malformed request body |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Authenticated but not authorized |
| 404 | Not Found | ElementId or resource doesn't exist |
| 500 | Internal Server Error | Server-side error |
| 501 | Not Implemented | Optional feature not supported |

**Error Response Format:**

```json
{
  "detail": "Human-readable error message"
}
```

**Error Handling Best Practices:**

1. Return specific error messages that help diagnose the issue
2. Never expose internal implementation details in error messages
3. Log detailed errors server-side for debugging
4. Use 404 for missing ElementIds, not 400

### 4.3 Pagination Strategy

For endpoints returning arrays, implementations MAY support pagination:

**Offset/Limit (Simple):**

```
GET /objects?offset=100&limit=50
```

**Response with pagination metadata:**

```json
{
  "items": [...],
  "total": 500,
  "offset": 100,
  "limit": 50
}
```

**Cursor-Based (Recommended for large datasets):**

```
GET /objects?cursor=eyJpZCI6MTAwfQ&limit=50
```

**Response:**

```json
{
  "items": [...],
  "nextCursor": "eyJpZCI6MTUwfQ",
  "hasMore": true
}
```

### 4.4 Filtering and Query Parameters

**Standard Query Parameters:**

| Endpoint | Parameter | Description |
|----------|-----------|-------------|
| `/objecttypes` | `namespaceUri` | Filter by namespace |
| `/objects` | `typeId` | Filter by object type |
| `/objects` | `includeMetadata` | Include optional metadata |
| `/objects/{id}/related` | `relationshiptype` | Filter by relationship type |
| `/objects/{id}/value` | `maxDepth` | Control composition recursion |
| `/objects/{id}/history` | `startTime`, `endTime` | Time range filter |

**Parameter Handling:**

- Unknown parameters SHOULD be ignored (forward compatibility)
- Invalid parameter values MUST return 400 Bad Request
- Parameters are case-sensitive

### 4.5 Endpoint Implementation Details

#### 4.5.1 GET /namespaces

**Requirements:**

- MUST return all registered namespaces
- Each namespace MUST have `uri` and `displayName`
- Response MUST be an array (empty array if no namespaces)

#### 4.5.2 GET /objecttypes

**Requirements:**

- MUST return all type definitions
- MAY filter by `namespaceUri` query parameter
- Each type MUST have `elementId`, `displayName`, `namespaceUri`, `schema`

#### 4.5.3 GET /objects

**Requirements:**

- MUST return array of instances
- MAY filter by `typeId` query parameter
- When `includeMetadata=false` (default), return minimal fields only
- Performance: Consider pagination for large datasets

#### 4.5.4 GET /objects/{elementId}/related

**Requirements:**

- MUST return array of related objects
- If `relationshiptype` not specified, return ALL related objects
- Include `relationshipType` and `relationshipTypeInverse` in response
- Return empty array if no relationships exist

#### 4.5.5 GET /objects/{elementId}/value

**Requirements:**

- MUST return current value in VQT format
- MUST support `maxDepth` parameter
- MUST return 404 if ElementId doesn't exist
- Include `isComposition` in response for client awareness

#### 4.5.6 GET /objects/{elementId}/history

**Requirements:**

- MUST return array of historical VQT values
- MUST support `startTime` and `endTime` filtering
- MUST support `maxDepth` parameter
- If no time range specified, return all available history
- Consider limiting response size with pagination

#### 4.5.7 PUT /objects/{elementId}/value

**Requirements (if implemented):**

- MUST accept any JSON value
- MUST return success/failure indication
- MAY write back to control systems (with security considerations)
- MUST return 501 if not implemented

#### 4.5.8 PUT /objects/{elementId}/history

**Requirements (if implemented):**

- MUST accept timestamp + value pairs
- SHOULD implement audit logging for historical changes
- MUST return 501 if not implemented

---

## 5. Subscription System

### 5.1 Overview

The subscription system enables real-time data delivery to clients. It supports two delivery modes:

| Mode | Name | Delivery | Use Case |
|------|------|----------|----------|
| streaming | At Most Once | SSE streaming | Real-time dashboards |
| sync | Exactly Once | Polling | Reliable data collection |

### 5.2 Streaming: At Most Once (SSE Streaming)

**How it works:**

1. Client creates subscription via `POST /subscriptions`
2. Client registers items via `POST /subscriptions/{id}/register`
3. Client opens SSE stream via `GET /subscriptions/{id}/stream`
4. Server pushes updates as they occur
5. No delivery guarantee - if client disconnects, updates are lost (streaming mode)

**Connection Management:**

```
Client                                Server
  |                                     |
  |--- POST /subscriptions ------------>|
  |<-- { subscriptionId: "123" } -------|
  |                                     |
  |--- POST /subscriptions/123/register |
  |<-- { message: "Registered" } -------|
  |                                     |
  |--- GET /subscriptions/123/stream -->|
  |<-- SSE: [{"elementId": "s1", ...}]  |
  |<-- SSE: [{"elementId": "s2", ...}]  |
  |<-- ...ongoing stream...             |
```

**SSE Format:**

Each SSE message is a JSON array containing one or more updates:

```
[{"elementId": "sensor-001", "value": 72.5, "quality": "Good", "timestamp": "2025-01-08T10:30:00Z"}]
```

**Heartbeat/Keepalive:**

Implementations SHOULD send periodic keepalive messages to detect disconnected clients:

```
[{"heartbeat": true, "timestamp": "2025-01-08T10:30:00Z"}]
```

Recommended interval: 30 seconds

**Reconnection Handling:**

- When client reconnects, subscription state persists
- Updates during disconnection are lost (streaming mode guarantee)
- Client must call `/stream` again to resume
- Previous stream connection is invalidated

### 5.3 Sync: Exactly Once (Polling)

**How it works:**

1. Client creates subscription via `POST /subscriptions`
2. Client registers items via `POST /subscriptions/{id}/register`
3. Server queues updates as they occur
4. Client polls via `POST /subscriptions/{id}/sync`
5. Server returns and clears queued updates
6. Guaranteed delivery - updates persist until acknowledged

**Polling Flow:**

```
Client                                Server
  |                                     |
  |--- POST /subscriptions ------------>|
  |<-- { subscriptionId: "123" } -------|
  |                                     |
  |--- POST /subscriptions/123/register |
  |<-- { message: "Registered" } -------|
  |                                     |
  |                     [Server queues updates]
  |                                     |
  |--- POST /subscriptions/123/sync --->|
  |<-- [update1, update2, update3] -----|
  |                     [Queue cleared] |
  |                                     |
  |--- POST /subscriptions/123/sync --->|
  |<-- [] (empty - no new updates) -----|
```

**Message Persistence Requirements:**

- Updates MUST be queued until client calls `/sync`
- Queue MUST have a maximum size (recommended: 1000 items)
- When queue is full, oldest items MUST be evicted (FIFO)
- Only the most recent value per element is required

**Acknowledgment Semantics:**

- Calling `/sync` implicitly acknowledges previous updates
- Updates are removed from queue after successful `/sync` response
- If `/sync` fails, updates remain in queue

**Queue Management:**

```python
# Recommended queue behavior
MAX_QUEUE_SIZE = 1000

def add_update(queue, update):
    if len(queue) >= MAX_QUEUE_SIZE:
        queue.pop(0)  # Remove oldest (FIFO)
    queue.append(update)

def sync(queue):
    updates = queue.copy()
    queue.clear()
    return updates
```

### 5.4 MonitoredItems Lifecycle

**Registration:**

```json
POST /subscriptions/{id}/register
{
  "elementIds": ["sensor-001", "sensor-002"],
  "maxDepth": 1
}
```

- Registration is additive (multiple calls add more items)
- Invalid ElementIds return 404
- `maxDepth` applies to all items in this registration

**Unregistration:**

```json
POST /subscriptions/{id}/unregister
{
  "elementIds": ["sensor-001"],
  "maxDepth": 1
}
```

- Silently ignores ElementIds not in subscription
- `maxDepth` determines which child items to also remove

**Subscription Deletion:**

```
DELETE /subscriptions/{id}
```

- Removes all monitored items
- Closes any active SSE stream
- Releases server resources

### 5.5 Update Propagation Timing

**Expected Behavior:**

- Updates SHOULD be delivered within 100ms of data source change
- SSE streams SHOULD push updates immediately
- Sync queues may batch updates for efficiency

**Composition Elements:**

When monitoring a composition element with `maxDepth > 1`:

- Update triggered when any component changes
- Update includes full recursive value structure
- Implementations MAY debounce rapid component changes

---

## 6. Architecture Recommendations

*This section is informative (non-normative).*

### 6.1 Data Source Abstraction Pattern

**Recommended Architecture:**

```
┌─────────────────────────────────────────────────┐
│                  I3X API Server                 │
├─────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ Routers  │ │ Models   │ │ Subscription Mgr │ │
│  └────┬─────┘ └──────────┘ └────────┬─────────┘ │
│       │                             │           │
│  ┌────▼─────────────────────────────▼─────┐     │
│  │         Data Source Interface          │     │
│  │  (Abstract: get_instances, get_values) │     │
│  └────────────────┬───────────────────────┘     │
└───────────────────┼─────────────────────────────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
┌───▼───┐     ┌─────▼─────┐    ┌────▼────┐
│ Mock  │     │   MQTT    │    │ OPC UA  │
│Source │     │  Source   │    │ Source  │
└───────┘     └───────────┘    └─────────┘
```

**Benefits:**

- Routers never import data sources directly
- Easy to add new data source types
- Enables multi-source routing for performance

### 6.2 Suggested Internal Interfaces

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Callable

class I3XDataSource(ABC):
    """Abstract interface for I3X data sources"""

    @abstractmethod
    def start(self, update_callback: Optional[Callable] = None) -> None:
        """Initialize and start the data source"""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop and cleanup the data source"""
        pass

    @abstractmethod
    def get_namespaces(self) -> List[Dict[str, Any]]:
        """Return array of Namespaces"""
        pass

    @abstractmethod
    def get_object_types(self, namespace_uri: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return array of Type definitions"""
        pass

    @abstractmethod
    def get_instances(self, type_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return array of instances"""
        pass

    @abstractmethod
    def get_instance_by_id(self, element_id: str) -> Optional[Dict[str, Any]]:
        """Return instance by ElementId"""
        pass

    @abstractmethod
    def get_instance_values_by_id(
        self,
        element_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        max_depth: int = 1,
        return_history: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Return instance values with optional recursion"""
        pass

    @abstractmethod
    def get_related_instances(
        self,
        element_id: str,
        relationship_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return related objects"""
        pass

    @abstractmethod
    def update_instance_value(self, element_id: str, value: Any) -> Dict[str, Any]:
        """Update value for element"""
        pass
```

### 6.3 Thread Safety Considerations

**Subscription System:**

- Subscription list access must be thread-safe
- Update callbacks may be invoked from multiple threads
- SSE streams run in async context; queue access needs synchronization

**Recommended Patterns:**

```python
import threading
from collections import defaultdict

class SubscriptionManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._subscriptions = {}

    def add_subscription(self, sub_id, subscription):
        with self._lock:
            self._subscriptions[sub_id] = subscription

    def get_subscription(self, sub_id):
        with self._lock:
            return self._subscriptions.get(sub_id)

    def route_update(self, element_id, value):
        with self._lock:
            subs = list(self._subscriptions.values())
        for sub in subs:
            if element_id in sub.monitored_items:
                sub.queue_update(element_id, value)
```

### 6.4 Caching Strategies

**Type/Namespace Caching:**

- Types and namespaces change infrequently
- Cache on startup, refresh periodically or on-demand
- Consider cache invalidation on configuration changes

**Instance Metadata Caching:**

- Cache instance metadata (not values)
- Values should always be fetched fresh
- Use LRU cache with reasonable TTL

**Value Caching:**

- Generally avoid caching values
- If caching, use very short TTL (< 1 second)
- Consider caching only for sync polling batching

### 6.5 Performance Guidelines

**Response Time Targets:**

| Operation | Target | Maximum |
|-----------|--------|---------|
| Exploratory (GET /objects) | < 100ms | 5s |
| Current Value (GET /value) | < 50ms | 1s |
| Historical Value (GET /history) | < 500ms | 300s |
| Subscription Update Delivery | < 100ms | 1s |

**Optimization Strategies:**

1. **Pre-fetch address space**: Load types, namespaces on startup
2. **Connection pooling**: Reuse connections to data sources
3. **Batch operations**: Combine multiple value fetches
4. **Async I/O**: Use async for SSE streams and data source calls
5. **Index by ElementId**: O(1) lookup for instances

---

## 7. Security

### 7.1 Transport Encryption

**Requirements:**

- Implementations MUST require encrypted transport (HTTPS) in production
- TLS 1.2 or higher SHOULD be used
- Self-signed certificates MAY be used for development only

### 7.2 Authentication Methods

**API Key (Required Minimum):**

```
X-API-Key: sk_live_abc123...
```

- MUST be transmitted over HTTPS only
- SHOULD be rotatable without service interruption
- SHOULD have configurable expiration

**JWT/OAuth (Optional):**

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

- MAY replace or supplement API keys
- Enables fine-grained authorization
- Supports token refresh without re-authentication

### 7.3 Authorization Patterns

**Recommended Authorization Model:**

| Permission | Description |
|------------|-------------|
| `read:exploratory` | Browse namespaces, types, instances |
| `read:values` | Query current and historical values |
| `write:values` | Update current values |
| `write:history` | Update historical values |
| `manage:subscriptions` | Create/delete subscriptions |

**Implementation:**

- Check permissions on every request
- Return 403 Forbidden for authorization failures
- Log authorization failures for security monitoring

### 7.4 Input Validation

**ElementId Validation:**

- Validate format before database lookup
- Prevent injection attacks (SQL, NoSQL, command)
- Limit maximum length (recommended: 256 characters)

**Query Parameter Validation:**

- Validate `maxDepth` is non-negative integer
- Validate `startTime`/`endTime` are valid RFC 3339
- Sanitize `namespaceUri` and `typeId` for injection

**Request Body Validation:**

- Validate JSON structure matches expected schema
- Limit request body size (recommended: 1MB)
- Validate array lengths for batch operations

---

## 8. Compliance Testing

### 8.1 Test Suite Overview

The compliance test suite (`compliance/`) validates RFC 001 conformance:

```
compliance/
├── README.md           # Test runner instructions
├── test_runner.py      # Python test runner
├── exploratory/        # RFC 4.1.x tests
├── values/             # RFC 4.2.1-4.2.2 tests
└── subscriptions/      # RFC 4.2.3 tests
```

### 8.2 Running Compliance Tests

```bash
cd spec/compliance
python test_runner.py --base-url http://localhost:8080
```

**Options:**

```
--base-url URL      Base URL of the I3X server (required)
--category NAME     Run only specific category (exploratory, values, subscriptions)
--required-only     Run only required tests (skip optional)
--verbose          Show detailed test output
```

### 8.3 Test Categories

| Category | Required | Tests |
|----------|----------|-------|
| exploratory | Yes | Namespaces, types, instances, relationships |
| values | Partially | Current value (req), history (opt), updates (opt) |
| subscriptions | Partially | Create/delete (req), streaming/sync (opt) |

### 8.4 Certification Levels

| Level | Requirements |
|-------|--------------|
| **Core** | All required exploratory + current value tests pass |
| **Extended** | Core + historical value + subscription tests pass |
| **Full** | Extended + value update tests pass |

---

## Appendix A: Quick Reference

### A.1 Endpoint Summary

| Method | Endpoint | RFC | Required |
|--------|----------|-----|----------|
| GET | /namespaces | 4.1.1 | Yes |
| GET | /objecttypes | 4.1.3 | Yes |
| GET | /objecttypes/{id} | 4.1.2 | Yes |
| GET | /relationshiptypes | 4.1.4 | Yes |
| GET | /relationshiptypes/{id} | 4.1.4 | Yes |
| GET | /objects | 4.1.5 | Yes |
| GET | /objects/{id} | 4.1.7 | Yes |
| GET | /objects/{id}/related | 4.1.6 | Yes |
| GET | /objects/{id}/value | 4.2.1.1 | Yes |
| GET | /objects/{id}/history | 4.2.1.2 | No |
| PUT | /objects/{id}/value | 4.2.2.1 | No |
| PUT | /objects/{id}/history | 4.2.2.2 | No |
| POST | /subscriptions | 4.2.3.1 | No |
| GET | /subscriptions/{id} | - | No |
| DELETE | /subscriptions/{id} | 4.2.3.5 | No |
| POST | /subscriptions/{id}/register | 4.2.3.2 | No |
| POST | /subscriptions/{id}/unregister | 4.2.3.3 | No |
| GET | /subscriptions/{id}/stream | 4.2.3.2 | No |
| POST | /subscriptions/{id}/sync | 4.2.3.4 | No |

### A.2 Common Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Invalid request |
| 401 | Authentication required |
| 403 | Not authorized |
| 404 | Not found |
| 500 | Server error |
| 501 | Not implemented |

### A.3 Quality Values

| Value | Meaning |
|-------|---------|
| Good | Valid, current |
| GoodNoData | Connected, no data |
| Bad | Invalid/failed |
| Uncertain | Unknown quality |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-01-27 | Initial release |

---

*Copyright (C) CESMII, the Smart Manufacturing Institute, 2024-2025. All Rights Reserved.*
