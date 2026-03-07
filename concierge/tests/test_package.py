"""Smoke tests for the concierge package."""


def test_concierge_package_imports():
    import concierge

    assert hasattr(concierge, "__version__")


def test_concierge_version_is_string():
    import concierge

    assert isinstance(concierge.__version__, str)
    assert concierge.__version__ == "0.1.0"
