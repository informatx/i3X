# Ignition CNC Data Source - Adaptation Notes

This document tracks the adaptations made (or not made) when converting the original Ignition/OPC UA payload format to the I3X API mock data source.

## Completed Adaptations

### #1 Element IDs - Base64 Encoding
**Status:** Kept original format

The original payload used Base64-encoded element IDs derived from paths like `[default]_types_/profiles/CNC/CNCBaseType`. We preserved this format.

**Rationale:** These IDs are opaque identifiers. While human-readable IDs would be easier to debug, keeping the original format ensures compatibility with any systems that expect the Base64 format.

**Implementation:** `ignition_cnc_data.py` uses `_encode_id()` helper to generate Base64 IDs matching the original pattern (with padding stripped).

---

### #2 Parameters Field in Schemas
**Status:** Kept original format

The original payload included a `parameters` field in type schemas with OPC UA-specific metadata:
```json
"parameters": {
    "NamespaceUri": "http://cesmii.net/profiles/CNC",
    "UAPrefix": null,
    "UAServer": null
}
```

**Rationale:** RFC 001 allows additional vendor-specific metadata in schemas. This field passes through harmlessly and preserves OPC UA context that may be useful to other systems.

**Implementation:** Added `parameters` to all type definitions in the Namespaces/*.json schema files.

---

### #3 `!related` Field in Schemas
**Status:** Kept original format

The original payload embedded relationship hints in type schemas:
```json
"!related": {
    "HasComponent": [
        "http://cesmii.net/profiles/CNC:W2RlZmF1bHRdX3R5cGVzXy8uLi4",
        ...
    ]
}
```

**Rationale:** This is an OPC UA pattern for defining type-level composition (what component types a parent type should contain). In I3X, relationships are declared on instances, not types. However:
- The field passes through harmlessly (RFC allows extra metadata)
- It documents the intended type hierarchy
- It could be useful for tools that generate instances from type definitions

**Important:** I3X clients won't interpret `!related` to understand composition. The actual relationships must be declared on instances via their `relationships` field. Our implementation does this correctly in `ignition_cnc_data.py`.

---

### #5 `!related` Reference Format
**Status:** Kept original format

References in `!related` use the `namespace:Base64Id` format:
```
"http://cesmii.net/profiles/CNC:W2RlZmF1bHRdX3R5cGVzXy9wcm9maWxlcy9DTkMvQ2hhbm5lbFR5cGU"
```

**Rationale:** Matches the original payload. The format encodes both the namespace URI and the type's element ID, which is useful for cross-namespace references.

---

### #4 Property Types - All Strings
**Status:** Reverted to original format (all strings)

The original payload used `"type": "string"` for all properties, regardless of semantic data type:
```json
"PowerConsumption": {
    "type": "string",
    "description": "kWh"
}
"AlarmActive": {
    "type": "string"
}
```

**Rationale:** The original developer's environment (Ignition/OPC UA) likely transmits all values as strings. Type coercion happens at the application layer, not the schema layer. Matching this format ensures compatibility.

**Properties changed back to string:**
- `Identification.YearOfConstruction` (was `integer`)
- `MachineStatusType.AlarmActive` (was `boolean`)
- `ICoolantTankType.LowLevelAlarm` (was `boolean`)
- `ToolStatusType.InUse` (was `boolean`)
- `AxisType.IsHomed` (was `boolean`)
- `Motor.Amps` (was `number`)
- `Motor.Running` (was `boolean`)
- `Motor.Fault` (was `boolean`)

**Recommendation:** For production implementations, consider using proper JSON Schema types (`integer`, `number`, `boolean`) to enable:
- Client-side schema validation
- Automatic type coercion in API clients
- Better documentation of expected data formats
- IDE/tooling support for type checking

The trade-off is compatibility vs. validation. If the source system guarantees type safety, specific types are preferred.

---

## Architecture Notes

### Type-Level vs Instance-Level Relationships

The original developer embedded `!related` in type schemas, following OPC UA's type composition model. In I3X:

| Concept | OPC UA Approach | I3X Approach |
|---------|----------------|--------------|
| "CNCBaseType has SpindleType components" | Defined in type schema via `!related` | Not enforced at type level |
| "cnc-machine-001 has spindle-001" | Implied by type definition | Explicitly declared in instance `relationships` |

Our implementation handles this correctly:
- `!related` passes through in schemas (for documentation)
- Actual relationships are declared on instances in `ignition_cnc_data.py`
- The `/objects/related` endpoint queries instance relationships, not type schemas

---

### Missing Instances - Root Cause of Test Failures

The original payload (`travis-payload.json`) contained **only type definitions** - no instances were provided. This is likely why client tests were failing.

**What the original payload had:**
- Object type schemas with `$ref`, `!related`, `!PropertyName` patterns
- Detailed type composition embedded in schemas

**What was missing:**
- Instance objects (actual equipment like `cnc-machine-001`)
- Instance relationships (`HasComponent`, `HasParent`)
- Instance values (VQT records)

**Impact on I3X API:**
| Endpoint | With Types Only | With Types + Instances |
|----------|-----------------|------------------------|
| `GET /objecttypes` | Works | Works |
| `GET /objects` | Empty/fails | Returns instances |
| `GET /objects/{id}/value` | Fails (nothing to query) | Returns VQT values |
| Subscriptions | Nothing to monitor | Can monitor instance changes |

**The misunderstanding:** The original developer may have expected the rich type schemas (`$ref`, nested structures, `!related`) to automatically provide or imply instance data. In I3X, types define **structure**, but instances must be explicitly created to hold **actual data**.

**Our solution:** Created mock instances in `ignition_cnc_data.py` with:
- Instance hierarchy (shop floor → machine → spindles/axes/channels)
- Explicit relationships on each instance
- VQT records with simulated values
- Background updater for live value simulation
