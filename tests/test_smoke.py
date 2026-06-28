import pytest


@pytest.mark.m0
def test_import():
    import tax_graph

    assert tax_graph.__version__ == "0.1.0"
