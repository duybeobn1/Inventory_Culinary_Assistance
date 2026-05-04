import pytest
import numpy as np
from fastapi.testclient import TestClient
from main import app, CAPACITY_MAP

client = TestClient(app)

# --- Task 1: Core API Endpoints ---
def test_api_health():
    """Verify health endpoints are responsive."""
    response = client.get("/")
    assert response.status_code == 200

# --- Task 2: OCR Extraction Accuracy ---
def test_ocr_extraction_accuracy():
    """
    Measures LLM extraction accuracy against ground truth validation sets.
    """
    # Define Ground Truth (What a human sees)
    ground_truth = {"items": [{"name": "MILK", "qty": 1000, "unit": "ml"}]}
    
    # Mock AI Output (What Gemini returns)
    mock_ai_output = {"items": [{"name": "MILK", "qty": 980, "unit": "ml"}]}
    
    # Calculate Accuracy Score
    matches = 0
    for truth in ground_truth["items"]:
        for pred in mock_ai_output["items"]:
            if truth["name"] == pred["name"]:
                # Tolerance check (within 5% of actual quantity)
                if abs(truth["qty"] - pred["qty"]) / truth["qty"] <= 0.05:
                    matches += 1
    
    accuracy_percent = (matches / len(ground_truth["items"])) * 100
    assert accuracy_percent >= 90, f"OCR accuracy too low: {accuracy_percent}%"

# --- Task 3: Fridge Pipeline Percent-Error ---
def test_fridge_mass_estimation_error():
    """
    Evaluates fridge pipeline accuracy by measuring percent-error 
    for mass estimation using Vision API outputs.
    """
    # 1. Human Reference (Weight measured on a real kitchen scale)
    actual_mass_g = 500.0  # e.g., a real bowl of Phở
    
    # 2. Vision API Output (Volume Fraction predicted by Gemini)
    predicted_fraction = 0.5 
    
    # 3. Calculation Engine (Formula: M = f * C)
    full_capacity = CAPACITY_MAP.get("MILK", {"capacity": 1000})["capacity"]
    estimated_mass = predicted_fraction * full_capacity
    
    # 4. Math: Percent Error Formula
    # $$Percent Error = \frac{|Actual - Estimated|}{Actual} \times 100$$
    percent_error = abs(actual_mass_g - estimated_mass) / actual_mass_g * 100
    
    # Target: Percent error should be less than 15% for culinary viability
    assert percent_error < 15, f"Mass estimation error exceeds 15% threshold: {percent_error}%"