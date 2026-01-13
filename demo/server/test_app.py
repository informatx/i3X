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
        """Test RFC 4.1.2 - Object Type Definition"""
        response = self.client.get("/objecttypes/work-center-type")
        data = response.json()

        self.assertEqual(response.status_code, 200)

        # Test non-existent type
        response = self.client.get("/objecttypes/non-existent")
        self.assertEqual(response.status_code, 404)

    def test_instances_endpoint(self):
        """Test RFC 4.1.6 - Instances of an Object Type"""
        response = self.client.get("/objects")
        data = response.json()

        self.assertEqual(response.status_code, 200)

    def test_object_definition_endpoint(self):
        """Test RFC 4.1.8 - Object Definition"""
        response = self.client.get("/objects/pump-101")
        data = response.json()

        self.assertEqual(response.status_code, 200)

        # Test non-existent object
        response = self.client.get("/objects/non-existent")
        self.assertEqual(response.status_code, 404)

    def test_last_known_value_endpoint(self):
        """Test RFC 4.2.1.1 - Object Element LastKnownValue"""
        response = self.client.get("/objects/sensor-001/value")
        data = response.json()

        self.assertEqual(response.status_code, 200)

        # Test with maxDepth (0=infinite, 2=recurse to depth 2)
        response = self.client.get("/objects/pump-101/value?maxDepth=2")
        data = response.json()
        self.assertEqual(response.status_code, 200)

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
