import unittest
import json
from fastapi.testclient import TestClient
from app import app
from models import Namespace, ObjectType, ObjectInstanceMinimal
import threading
import time
import asyncio


class TestI3XEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    def test_namespaces_endpoint(self):
        """Test RFC 4.1.1 - Namespaces"""
        response = self.client.get("/namespaces")
        data = response.json()

        self.assertEqual(response.status_code, 200)

    def test_object_types_endpoint(self):
        """Test RFC 4.1.3 - Object Types"""
        response = self.client.get("/objecttypes")
        data = response.json()

        self.assertEqual(response.status_code, 200)

    def test_object_type_definition_endpoint(self):
        """Test RFC 4.1.2 - Object Type Definition (POST /objecttypes/query)"""
        # Test single elementId
        response = self.client.post("/objecttypes/query", json={"elementId": "work-center-type"})
        data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["totalRequested"], 1)
        self.assertEqual(data["totalSuccess"], 1)
        self.assertEqual(len(data["results"]), 1)
        self.assertTrue(data["results"][0]["success"])

        # Test non-existent type (returns success=false in results, not 404)
        response = self.client.post("/objecttypes/query", json={"elementId": "non-existent"})
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["totalFailed"], 1)
        self.assertFalse(data["results"][0]["success"])

    def test_object_type_definition_batch(self):
        """Test RFC 4.1.2 - Object Type Definition batch query"""
        response = self.client.post("/objecttypes/query", json={
            "elementIds": ["work-center-type", "non-existent"]
        })
        data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["totalRequested"], 2)
        self.assertEqual(data["totalSuccess"], 1)
        self.assertEqual(data["totalFailed"], 1)

    def test_instances_endpoint(self):
        """Test RFC 4.1.6 - Instances of an Object Type"""
        response = self.client.get("/objects")
        data = response.json()

        self.assertEqual(response.status_code, 200)

    def test_object_definition_endpoint(self):
        """Test RFC 4.1.8 - Object Definition (POST /objects/query)"""
        # Test single elementId
        response = self.client.post("/objects/query", json={"elementId": "cnc-001"})
        data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["totalRequested"], 1)
        self.assertEqual(data["totalSuccess"], 1)
        self.assertTrue(data["results"][0]["success"])

        # Test non-existent object (returns success=false in results, not 404)
        response = self.client.post("/objects/query", json={"elementId": "non-existent"})
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["totalFailed"], 1)
        self.assertFalse(data["results"][0]["success"])

    def test_object_definition_batch(self):
        """Test RFC 4.1.8 - Object Definition batch query"""
        response = self.client.post("/objects/query", json={
            "elementIds": ["cnc-001", "cnc-001-spindle", "non-existent"]
        })
        data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["totalRequested"], 3)
        self.assertEqual(data["totalSuccess"], 2)
        self.assertEqual(data["totalFailed"], 1)

    def test_last_known_value_endpoint(self):
        """Test RFC 4.2.1.1 - Object Element LastKnownValue (POST /objects/value)"""
        # Test single elementId
        response = self.client.post("/objects/value", json={"elementId": "cnc-001-status"})
        data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["totalRequested"], 1)
        self.assertEqual(data["totalSuccess"], 1)
        self.assertTrue(data["results"][0]["success"])
        self.assertIn("value", data["results"][0]["data"])

        # Test with maxDepth (0=infinite, 2=recurse to depth 2)
        response = self.client.post("/objects/value", json={"elementId": "cnc-001", "maxDepth": 2})
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["results"][0]["success"])

    def test_last_known_value_batch(self):
        """Test RFC 4.2.1.1 - LastKnownValue batch query"""
        response = self.client.post("/objects/value", json={
            "elementIds": ["cnc-001-status", "cnc-001-spindle"],
            "maxDepth": 1
        })
        data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["totalRequested"], 2)
        self.assertEqual(data["totalSuccess"], 2)

    def test_related_objects_endpoint(self):
        """Test RFC 4.1.6 - Related Objects (POST /objects/related)"""
        response = self.client.post("/objects/related", json={"elementId": "cnc-001"})
        data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["totalRequested"], 1)
        self.assertTrue(data["results"][0]["success"])

    def test_historical_values_endpoint(self):
        """Test RFC 4.2.1.2 - Historical Values (POST /objects/history)"""
        response = self.client.post("/objects/history", json={"elementId": "cnc-001-status"})
        data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["totalRequested"], 1)
        self.assertTrue(data["results"][0]["success"])

    def test_relationship_type_query_endpoint(self):
        """Test RFC 4.1.4 - Relationship Type query (POST /relationshiptypes/query)"""
        response = self.client.post("/relationshiptypes/query", json={"elementId": "HasComponent"})
        data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["totalRequested"], 1)
        # Note: success depends on whether HasComponent exists in the mock data

    def test_request_validation_errors(self):
        """Test request validation - must provide elementId or elementIds"""
        # Neither provided
        response = self.client.post("/objects/query", json={})
        self.assertEqual(response.status_code, 422)

        # Both provided
        response = self.client.post("/objects/query", json={
            "elementId": "cnc-001",
            "elementIds": ["cnc-001-spindle"]
        })
        self.assertEqual(response.status_code, 422)

    def test_hierarchical_relationships_endpoint(self):
        """Test RFC 4.1.4 - Relationship Types"""
        response = self.client.get("/relationshiptypes")
        data = response.json()

        self.assertEqual(response.status_code, 200)

    # TODO this probably belongs on the client side and is more than a unit test, placing here so I have a place to test subscriptions
    def test_qos0_subscription_streaming(self):
        # Step 1: Create a subscription (no QoS parameter)
        response = self.client.post("/subscriptions", json={})
        self.assertEqual(response.status_code, 200)
        subscription_id = response.json()["subscriptionId"]
        self.assertIsNotNone(subscription_id)

        # Step 2: Register monitored items
        register_url = f"/subscriptions/{subscription_id}/register"
        payload = {"elementIds": ["sensor-001"]}
        response = self.client.post(register_url, json=payload)
        self.assertEqual(response.status_code, 200)

        # Step 3: Start streaming
        stream_url = f"/subscriptions/{subscription_id}/stream"

        # We will run the streaming request in a separate thread to allow timeout
        results = []

        def stream_reader():
            with self.client.stream("GET", stream_url) as stream_resp:
                self.assertEqual(stream_resp.status_code, 200)
                count = 0
                for line in stream_resp.iter_lines():
                    if line:
                        decoded = line.decode("utf-8")
                        print("Received chunk:", decoded)
                        results.append(decoded)
                        count += 1
                        if count >= 3:  # read 3 update batches then stop
                            break

        thread = threading.Thread(target=stream_reader)
        thread.start()
        thread.join(timeout=10)

        # Check that we got streaming data and parseable JSON
        self.assertGreaterEqual(
            len(results), 1, "Did not receive any streaming updates"
        )

        for chunk in results:
            data = json.loads(chunk)
            self.assertIsInstance(data, list)
            self.assertTrue(all("elementId" in update for update in data))


if __name__ == "__main__":
    unittest.main()
