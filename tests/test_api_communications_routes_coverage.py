"""Tests for communications routes coverage.

Note: The file pbx/api/routes/communications.py does not exist in this codebase.
Communication-related endpoints are implemented in other route modules
(calls.py, webrtc.py, etc.). This file validates that there is no
communications blueprint by testing that the expected module does not exist.
"""

import importlib

import pytest


@pytest.mark.unit
class TestCommunicationsModuleExists:
    """Verify that the communications route module state is as expected."""

    def test_communications_module_does_not_exist(self) -> None:
        """The communications route module should not be importable."""
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("pbx.api.routes.communications")
