from fastapi.testclient import TestClient
from main import app
import os

client = TestClient(app)

def test_read_root():
    """Test the root endpoint for server availability."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "Serverless Backend API is running!"}

def test_db_health_config_error():
    """
    Test the DB health check when DATABASE_URL is missing.
    This simulates a CI environment without .env secrets.
    """
    # Temporarily remove DATABASE_URL if it exists in the test environment
    original_url = os.environ.get("DATABASE_URL")
    if "DATABASE_URL" in os.environ:
        del os.environ["DATABASE_URL"]
    
    response = client.get("/health/db")
    # According to our main.py logic, it returns a 200 with an error message in JSON
    assert response.status_code == 200
    assert "Configuration Error" in response.json()["database"]
    
    # Restore for other tests
    if original_url:
        os.environ["DATABASE_URL"] = original_url

def test_gemini_config_check():
    """Check if the parse endpoint handles missing API keys gracefully."""
    response = client.post("/api/receipt/parse")
    # Should return an error about configuration or missing file, not a 500 crash
    assert response.status_code in [200, 422]
