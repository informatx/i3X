# I3X API Response Formats

This document describes the response formats used by the I3X API. See `response-schemas.json` for formal JSON Schema definitions.

3 main response formats are described:

```
┌─────────────────┬───────────────────────────────────────┬────────────────────────────────────┬─────────────────────────────────────────────────┐
│     Format      │               Endpoints               │             Structure              │                     Example                     │
├─────────────────┼───────────────────────────────────────┼────────────────────────────────────┼─────────────────────────────────────────────────┤
│ Object Metadata │ GET /objects                          | Array of objects with static       |                                                 |
|                 | POST /objects/list                    │ metadata.                          │ [{"elementId": "...", "displayName": "...",     │
│                 │ POST /objects/related                 │                                    │ "typeId": "...", "isComposition": true}]        │
├─────────────────┼───────────────────────────────────────┼────────────────────────────────────┼─────────────────────────────────────────────────┤
│ Value Response  │ POST /objects/value                   │ Dict keyed by elementId, data =    │ {"sensor-001": {"data": [{"value": 67.1,        │
│                 │ POST /objects/history                 │ VQT array, other keys = children   │ "quality": "GOOD", "timestamp": "..."}]}}       │
├─────────────────┼───────────────────────────────────────┼────────────────────────────────────┼─────────────────────────────────────────────────┤
│ Subscription    │ GET /subscriptions/{id}/stream (SSE)  │ Same as Value Response (single     │ {"sensor-001": {"data": [{"value": 67.1,        │
│ Stream          │                                       │ element)                           │ ...}]}}                                         │
├─────────────────┼───────────────────────────────────────┼────────────────────────────────────┼─────────────────────────────────────────────────┤
│ Subscription    │ GET /subscriptions/{id}/sync          │ Same as Value Response (but in     │ [{"sensor-001": {"data": [...]}}, {"pump-101":  │
│ Sync            │                                       │ an array)                          │ {"data": [...]}}]                               │
├─────────────────┼───────────────────────────────────────┼────────────────────────────────────┼─────────────────────────────────────────────────┤
│ Update Result   │ PUT /objects/{elementId}/value        │ Operation result                   │ {"elementId": "...", "success": true,           │
│                 │                                       │                                    │ "message": "Updated successfully"}              │
└─────────────────┴───────────────────────────────────────┴────────────────────────────────────┴─────────────────────────────────────────────────┘
```

## Core Concepts

### VQT (Value-Quality-Timestamp)
The standard structure for time-series data from a data source:
```json
{
  "value": <any>,
  "quality": "GOOD",
  "timestamp": "2025-10-28T18:20:44.779036+00:00"
}
```

### Composition and the `data` Key
Elements with `isComposition: true` have their data composed of HasComponent children. The reserved key `data` holds an element's own VQT array. Any other key is a child elementId.

**Rule:** In a value response, `data` = this element's VQT array, everything else = child element.

---

## Response Schemas

### 1. Object Metadata

**Endpoints:** `GET /objects`, `POST /objects/list`, `POST /objects/related`

Static metadata describing object instances. Does not include time-series values.

```json
[
  {
    "elementId": "pump-101",
    "displayName": "pump-101",
    "typeId": "work-unit-type",
    "namespaceUri": "https://isa.org/isa95",
    "parentId": "pump-station",
    "isComposition": true
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| elementId | string | Unique identifier |
| displayName | string | Human-readable name |
| typeId | string | Reference to object type definition |
| namespaceUri | string | Namespace URI |
| parentId | string/null | Parent element ID ("/" for root) |
| isComposition | boolean | True if value composed of HasComponent children |

---

### 2. Value Response

**Endpoints:** `POST /objects/value`, `POST /objects/history`

Time-series values with nested composition structure.

#### Simple value (leaf element):
```json
{
  "sensor-001": {
    "data": [
      {"value": 67.1, "quality": "GOOD", "timestamp": "2025-10-28T10:15:30Z"}
    ]
  }
}
```

#### Historical values:
```json
{
  "sensor-001": {
    "data": [
      {"value": 67.1, "quality": "GOOD", "timestamp": "2025-10-28T10:15:30Z"},
      {"value": 54.9, "quality": "GOOD", "timestamp": "2025-10-27T10:15:30Z"},
      {"value": 68.2, "quality": "GOOD", "timestamp": "2025-10-26T10:15:30Z"}
    ]
  }
}
```

#### Multiple elements:
```json
{
  "sensor-001": {
    "data": [
      {"value": 67.1, "quality": "GOOD", "timestamp": "2025-10-28T10:15:30Z"}
    ]
  },
  "pump-101-state": {
    "data": [
      {"value": {"description": "Running"}, "quality": "GOOD", "timestamp": "2025-10-28T18:20:44Z"}
    ]
  }
}
```

#### Composition element (with maxDepth > 1):
```json
{
  "pump-101-measurements": {
    "data": [],
    "pump-101-bearing-temperature": {
      "data": [
        {"value": {"inTolerance": true, "tolerance": 5.0}, "quality": "GOOD", "timestamp": "2025-10-28T18:20:44Z"}
      ],
      "pump-101-measurements-bearing-temperature-value": {
        "data": [
          {"value": 70.34, "quality": "GOOD", "timestamp": "2025-10-28T18:32:47Z"}
        ]
      },
      "pump-101-measurements-bearing-temperature-health": {
        "data": [
          {"value": 12, "quality": "GOOD", "timestamp": "2025-10-28T18:32:47Z"}
        ]
      }
    }
  }
}
```

| Key | Type | Description |
|-----|------|-------------|
| `data` | array[VQT] | This element's VQT values (reserved key) |
| `<elementId>` | object | Child element (HasComponent relationship) |

---

### 3. Subscription Updates

**Endpoints:** `GET /subscriptions/{id}/sync`, `GET /subscriptions/{id}/stream` (SSE)

Same structure as value response.

#### Single update (SSE stream event):
```json
{
  "sensor-001": {
    "data": [
      {"value": 67.1, "quality": "GOOD", "timestamp": "2025-10-28T10:15:30Z"}
    ]
  }
}
```

#### Sync response (array of pending updates):
```json
[
  {
    "sensor-001": {
      "data": [
        {"value": 67.1, "quality": "GOOD", "timestamp": "2025-10-28T10:15:30Z"}
      ]
    }
  },
  {
    "pump-101-state": {
      "data": [
        {"value": {"description": "Pump is running"}, "quality": "GOOD", "timestamp": "2025-10-29T18:20:44Z"}
      ]
    }
  }
]
```

---

### 4. Update Result

**Endpoints:** `PUT /objects/{elementId}/value`

Result of a write operation.

```json
{
  "elementId": "sensor-001",
  "success": true,
  "message": "Updated successfully"
}
```

| Field | Type | Description |
|-------|------|-------------|
| elementId | string | Element that was updated |
| success | boolean | True if update succeeded |
| message | string | Human-readable result |

---

## Design Rationale

### Why `data` as the reserved key?
- Distinguishes an element's own VQT values from its children
- `data[0].value` reads better than `values[0].value`
- Simple rule: `data` = own values, anything else = child elementId

### Why nested structure for composition?
- Shows parent-child relationships through nesting
- Client can discover composition via exploratory endpoints (`isComposition`, `HasComponent`)
- No redundant `elementId` fields inside each entry
- Hierarchy is visually clear in the JSON structure

### Why same structure for value, history, and subscriptions?
- Consistent parsing logic for clients
- `data` array has 1 element for current value, N elements for history
- Subscriptions use identical format for seamless integration
