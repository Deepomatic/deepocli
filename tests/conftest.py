from gevent.monkey import patch_all
patch_all(thread=False, time=False, subprocess=False)
import pytest


@pytest.fixture
def no_error_logs(caplog):
    yield

    records = caplog.get_records('call')
    # Check we got no log in error
    for log in records:
        assert log.levelname not in {'ERROR', 'CRITICAL'}
