"""Tests for launchd plist generator."""
from pathlib import Path

import pytest

from concierge.setup.launchd import generate_plist, install_plist


class TestGeneratePlist:
    def test_generate_plist_contains_label(self):
        """Generated plist should contain the provided label."""
        plist = generate_plist(label="com.test.agent")
        assert "<string>com.test.agent</string>" in plist

    def test_generate_plist_contains_interval(self):
        """Generated plist should contain the specified interval."""
        plist = generate_plist(interval_seconds=1800)
        assert "<integer>1800</integer>" in plist

    def test_generate_plist_run_at_load_true(self):
        """run_at_load=True should produce <true/> in plist."""
        plist = generate_plist(run_at_load=True)
        assert "<true/>" in plist

    def test_generate_plist_run_at_load_false(self):
        """run_at_load=False should produce <false/> in plist."""
        plist = generate_plist(run_at_load=False)
        assert "<false/>" in plist

    def test_generate_plist_custom_paths(self):
        """Custom working_dir and python_path should appear in the plist."""
        plist = generate_plist(
            working_dir="/opt/bureau",
            python_path="/usr/local/bin/python3.13",
        )
        assert "<string>/opt/bureau</string>" in plist
        assert "<string>/usr/local/bin/python3.13</string>" in plist


class TestInstallPlist:
    def test_install_plist_writes_file(self, tmp_path, monkeypatch):
        """install_plist should write the plist to the LaunchAgents directory."""
        # Override Path.home() to use tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        plist_content = generate_plist(label="com.test.install")
        result_path = install_plist(plist_content, label="com.test.install")
        assert result_path.exists()
        assert result_path.name == "com.test.install.plist"
        assert plist_content in result_path.read_text()
