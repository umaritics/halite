from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
response = client.get("/api/health")
print(response.json())
