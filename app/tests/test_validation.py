from app.schemas import ComplianceCheckRequest
import pytest

def test_validation_non_empty():
    with pytest.raises(ValueError):
        ComplianceCheckRequest(text="   ")

def test_validation_long_text():
    bad = "x" * 9000
    with pytest.raises(ValueError):
        ComplianceCheckRequest(text=bad)
