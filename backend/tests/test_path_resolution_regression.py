import os
import sys
import pytest
from pathlib import Path

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.utils.path_utils import find_synthetic_data_dir, REQUIRED_CSV_FILES

def test_find_synthetic_data_dir_resolution():
    """
    Regression test: Verifies that find_synthetic_data_dir() resolves a valid directory Path
    that exists and contains all 5 required CSV files.
    """
    resolved_dir_str = find_synthetic_data_dir()
    resolved_path = Path(resolved_dir_str)

    # Assert directory exists and is a directory
    assert resolved_path.exists(), f"Resolved path '{resolved_path}' does not exist on filesystem"
    assert resolved_path.is_dir(), f"Resolved path '{resolved_path}' is not a directory"

    # Assert all 5 expected CSV files exist inside the resolved directory
    for csv_name in REQUIRED_CSV_FILES:
        csv_file = resolved_path / csv_name
        assert csv_file.exists(), f"Required CSV file '{csv_name}' is missing in resolved directory '{resolved_path}'"
        assert csv_file.is_file(), f"'{csv_name}' in '{resolved_path}' is not a regular file"
        assert csv_file.stat().st_size > 0, f"CSV file '{csv_name}' in '{resolved_path}' is empty (0 bytes)"

    print(f"\n[REGRESSION TEST PASSED] find_synthetic_data_dir() cleanly resolved to '{resolved_path}' containing all 5 required non-empty CSV files.")

if __name__ == "__main__":
    test_find_synthetic_data_dir_resolution()
