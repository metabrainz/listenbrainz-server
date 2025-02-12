import logging
import pytest
import sys

print("Loading conftest.py configuration...", flush=True)

# Configure root logger to output all levels to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

@pytest.hookimpl(tryfirst=True)
def pytest_runtest_protocol(item, nextitem):
    item.config.pluginmanager.get_plugin("terminalreporter").write_line(
        f"\n{'='*80}\nStarting test: {item.nodeid}\n{'='*80}"
    )

# Optional: Add a session start hook to verify logging is working
@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    print("\nTest session started - logging check", flush=True)
    logger.info("Test session started - logging check") 
