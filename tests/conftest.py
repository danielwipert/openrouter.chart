import pytest

import sizes


@pytest.fixture(autouse=True)
def no_hugging_face_calls(monkeypatch):
    """Tests never call Hugging Face: every repo is 'not listed' unless a test says so."""
    monkeypatch.setattr(sizes, "hf_lookup", lambda repo: None)
