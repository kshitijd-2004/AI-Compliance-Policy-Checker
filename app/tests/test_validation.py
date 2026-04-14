import pytest

from app.schemas import ComplianceCheckRequest


def test_validation_non_empty():
    with pytest.raises(ValueError):
        ComplianceCheckRequest(text="   ")


def test_validation_long_text():
    with pytest.raises(ValueError):
        ComplianceCheckRequest(text="x" * 9000)
