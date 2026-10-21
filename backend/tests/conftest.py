import pytest


@pytest.fixture(autouse=True)
def _reset_query_limiter():
    """The rate limiter is process-global; keep tests from exhausting each other's quota."""
    from precis.api.security import query_limiter

    query_limiter._requests.clear()
    yield
    query_limiter._requests.clear()
