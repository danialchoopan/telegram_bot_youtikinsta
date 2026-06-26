"""
==========================================
  Unit Tests - Quality Optimizer
==========================================

Tests for the media optimization functionality.
Note: These tests require ffmpeg to be installed.
"""

import pytest
import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Skip all tests if ffmpeg not available
pytest.importorskip("subprocess")

from bot.services.optimizer import QualityOptimizer


class TestOptimizer:
    """Test quality optimizer functionality."""

    @pytest.fixture
    def optimizer(self):
        """Create optimizer instance."""
        return QualityOptimizer()

    def test_get_output_ext_mp4(self, optimizer):
        assert optimizer._get_output_ext("mp4") == ".mp4"

    def test_get_output_ext_mkv(self, optimizer):
        assert optimizer._get_output_ext("mkv") == ".mkv"

    def test_get_output_ext_mp3(self, optimizer):
        assert optimizer._get_output_ext("mp3") == ".mp3"

    def test_get_output_ext_m4a(self, optimizer):
        assert optimizer._get_output_ext("m4a") == ".m4a"

    def test_get_output_ext_best(self, optimizer):
        assert optimizer._get_output_ext("best") == ".mp4"

    def test_get_output_ext_unknown(self, optimizer):
        assert optimizer._get_output_ext("unknown") == ".mp4"

    def test_file_not_found(self, optimizer):
        with pytest.raises(FileNotFoundError):
            optimizer.optimize("/nonexistent/file.mp4", "mp4")

    @patch("bot.services.optimizer.Config")
    def test_already_optimized_mp3(self, mock_config, optimizer):
        # Create a temporary .mp3 file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_path = f.name

        try:
            # Mock config to disable thumbnail extraction
            mock_config.ENABLE_THUMBNAIL_EXTRACTION = False
            mock_config.OPTIMIZED_PATH = Path(tempfile.mkdtemp())

            result = optimizer.optimize(temp_path, "mp3")
            assert result == temp_path  # Should return original
        finally:
            os.unlink(temp_path)

    def test_check_h264_nonexistent(self, optimizer):
        # Should return False for nonexistent file
        assert optimizer._check_h264("/nonexistent/file.mp4") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
