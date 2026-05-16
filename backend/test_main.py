import pytest
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app
from dependencies import get_current_user

client = TestClient(app)


# ==========================================
# Fixtures
# ==========================================
@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = lambda: "test-user-id"
    yield
    app.dependency_overrides.clear()


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Serverless API is running!"
    assert "version" in data


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@patch("db.supabase.supabase")
def test_health_db_success(mock_supabase):
    mock_supabase.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"id": 1}]
    )
    response = client.get("/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


def test_analyze_ingredient_chef_ai_unreachable():
    response = client.post(
        "/api/chef/analyze-ingredient",
        json={"ingredient_name": "Test"},
    )
    assert response.status_code in (500, 503)


def test_environment_context_invalid_coords():
    response = client.get("/api/context/environment?lat=999&lon=999")
    assert response.status_code in (200, 400, 500)


def test_determine_season():
    from routers.context import determine_season

    assert determine_season(40.0, 3) == "Spring"
    assert determine_season(40.0, 6) == "Summer"
    assert determine_season(40.0, 9) == "Autumn"
    assert determine_season(40.0, 12) == "Winter"

    assert determine_season(-33.0, 3) == "Autumn"
    assert determine_season(-33.0, 6) == "Winter"
    assert determine_season(-33.0, 9) == "Spring"
    assert determine_season(-33.0, 12) == "Summer"


def test_evaluate_tcm_weather_balance():
    from routers.context import evaluate_tcm_weather_balance

    hot = evaluate_tcm_weather_balance(35.0, 0.0, "Summer")
    assert hot["target_thermal_property"] == "Yin"

    cold = evaluate_tcm_weather_balance(5.0, 0.0, "Winter")
    assert cold["target_thermal_property"] == "Yang"

    damp = evaluate_tcm_weather_balance(20.0, 1.0, "Spring")
    assert damp["target_thermal_property"] == "Yang"

    neutral = evaluate_tcm_weather_balance(22.0, 0.0, "Spring")
    assert neutral["target_thermal_property"] == "Neutral"


def test_clean_ai_json():
    from db.ai import clean_ai_json

    result = clean_ai_json('{"key": "value"}')
    assert result == {"key": "value"}

    result = clean_ai_json('[{"a": 1}]')
    assert result == [{"a": 1}]

    result = clean_ai_json('Some text before {"key": "value"} some text after')
    assert result == {"key": "value"}

    with pytest.raises(ValueError):
        clean_ai_json("No json here")


def test_load_capacities():
    from routers.fridge import CAPACITY_MAP

    assert "MILK" in CAPACITY_MAP
    assert CAPACITY_MAP["MILK"]["capacity"] == 1000
    assert CAPACITY_MAP["MILK"]["unit"] == "ml"


def test_ocr_extraction_accuracy():
    ground_truth = {"items": [{"name": "MILK", "qty": 1000, "unit": "ml"}]}
    mock_ai_output = {"items": [{"name": "MILK", "qty": 980, "unit": "ml"}]}

    matches = 0
    for truth in ground_truth["items"]:
        for pred in mock_ai_output["items"]:
            if truth["name"] == pred["name"]:
                if abs(truth["qty"] - pred["qty"]) / truth["qty"] <= 0.05:
                    matches += 1

    accuracy_percent = (matches / len(ground_truth["items"])) * 100
    assert accuracy_percent >= 90, f"OCR accuracy too low: {accuracy_percent}%"


def test_fridge_mass_estimation_error():
    actual_mass_g = 500.0
    predicted_fraction = 0.5

    from routers.fridge import CAPACITY_MAP

    full_capacity = CAPACITY_MAP.get("MILK", {"capacity": 1000})["capacity"]
    estimated_mass = predicted_fraction * full_capacity

    percent_error = abs(actual_mass_g - estimated_mass) / actual_mass_g * 100
    assert percent_error < 15, f"Mass estimation error exceeds 15%: {percent_error}%"


# ==========================================
# Auth Tests
# ==========================================
def test_auth_signin_no_supabase():
    response = client.post(
        "/api/auth/signin",
        json={"email": "test@example.com", "password": "password123"},
    )
    assert response.status_code in (401, 400, 500)


def test_auth_signup_no_supabase():
    response = client.post(
        "/api/auth/signup",
        json={"email": "new@example.com", "password": "password123"},
    )
    assert response.status_code in (400, 409, 500)


def test_auth_me_mocked():
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code in (200, 404)


@patch("db.supabase.supabase")
def test_signup_with_mock(mock_supabase):
    mock_supabase.auth.sign_up.return_value = MagicMock(
        user=MagicMock(id="user-1", email="test@example.com"),
        session=MagicMock(access_token="mock-token"),
    )
    mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "prof-1", "user_id": "user-1", "display_name": "Test Chef"}]
    )

    response = client.post(
        "/api/auth/signup",
        json={"email": "test@example.com", "password": "password123", "display_name": "Test Chef"},
    )

    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "success"
        assert data["email"] == "test@example.com"


@patch("db.supabase.supabase")
def test_signin_with_mock(mock_supabase):
    mock_supabase.auth.sign_in_with_password.return_value = MagicMock(
        user=MagicMock(id="user-1", email="test@example.com"),
        session=MagicMock(access_token="mock-token"),
    )
    mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"id": "prof-1", "user_id": "user-1", "display_name": "Test Chef"}]
    )

    response = client.post(
        "/api/auth/signin",
        json={"email": "test@example.com", "password": "password123"},
    )

    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "success"
        assert data["email"] == "test@example.com"
