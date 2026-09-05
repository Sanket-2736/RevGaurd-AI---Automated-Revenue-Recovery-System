import os
import logging
from pathlib import Path
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

REQUIRED_CSV_FILES = [
    "customers.csv",
    "payments.csv",
    "checkouts.csv",
    "subscriptions.csv",
    "invoices.csv",
]

def find_synthetic_data_dir() -> str:
    """
    Robustly resolves the absolute path to the synthetic-data directory regardless of launch directory.
    Checks SYNTHETIC_DATA_DIR env var first, then traverses upwards from __file__ and cwd using pathlib.
    """
    # 1. Check SYNTHETIC_DATA_DIR env variable
    env_dir = os.getenv("SYNTHETIC_DATA_DIR")
    if env_dir:
        env_path = Path(env_dir).resolve()
        logger.info(f"[PATH CHECK] Checking SYNTHETIC_DATA_DIR env var: '{env_path}'")
        if env_path.is_dir():
            logger.info(f"[PATH RESOLVED] Using SYNTHETIC_DATA_DIR: '{env_path}'")
            return str(env_path)
        else:
            logger.warning(f"[PATH WARNING] SYNTHETIC_DATA_DIR specified '{env_path}' but directory does not exist.")

    # 2. Derive base paths relative to this file and current working directory
    current_file = Path(__file__).resolve()
    cwd = Path.cwd().resolve()

    candidate_paths = [
        # Upward traversal from current file location (__file__)
        current_file.parent / "synthetic-data",                         # app/utils/synthetic-data
        current_file.parent.parent / "synthetic-data",                  # app/synthetic-data
        current_file.parent.parent.parent / "synthetic-data",           # backend/synthetic-data
        current_file.parent.parent.parent.parent / "synthetic-data",    # repo_root/synthetic-data

        # Upward traversal from current working directory (cwd)
        cwd / "synthetic-data",
        cwd.parent / "synthetic-data",
        cwd.parent.parent / "synthetic-data",

        # Standard container / linux mount point
        Path("/app/synthetic-data"),
        Path("/synthetic-data"),
    ]

    # Deduplicate while preserving order
    unique_candidates: List[Path] = []
    seen = set()
    for p in candidate_paths:
        try:
            resolved = p.resolve()
            if str(resolved) not in seen:
                seen.add(str(resolved))
                unique_candidates.append(resolved)
        except Exception:
            pass

    logger.info(f"[PATH SEARCH START] Searching for synthetic-data directory across {len(unique_candidates)} candidate paths...")

    for path_obj in unique_candidates:
        is_exist = path_obj.is_dir()
        logger.info(f"[PATH SEARCH] Testing path: '{path_obj}' -> Exists: {is_exist}")
        if is_exist:
            logger.info(f"[PATH RESOLVED SUCCESS] Located synthetic-data directory at: '{path_obj}'")
            return str(path_obj)

    err_msg = (
        f"Could not locate 'synthetic-data' directory. Checked candidates: "
        f"{[str(p) for p in unique_candidates]}. Please set SYNTHETIC_DATA_DIR env var."
    )
    logger.error(f"[PATH RESOLUTION CRITICAL FAIL] {err_msg}")
    raise FileNotFoundError(err_msg)

def verify_synthetic_data_on_startup() -> Tuple[bool, str, Dict[str, bool]]:
    """
    Startup verification check: resolves synthetic-data directory and validates existence of required CSVs.
    Logs detailed status to backend console.
    """
    try:
        data_dir = find_synthetic_data_dir()
        data_path = Path(data_dir)
        csv_status: Dict[str, bool] = {}
        all_found = True

        logger.info(f"======================================================================")
        logger.info(f"[STARTUP CHECK] Verifying Synthetic Data Directory: '{data_dir}'")

        for csv_name in REQUIRED_CSV_FILES:
            csv_file = data_path / csv_name
            exists = csv_file.is_file()
            csv_status[csv_name] = exists
            if exists:
                try:
                    with open(csv_file, "r", encoding="utf-8") as f:
                        line_count = sum(1 for _ in f) - 1
                    logger.info(f"[STARTUP CHECK]   ✔ {csv_name:<20} -> EXISTS ({max(0, line_count)} data rows)")
                except Exception:
                    logger.info(f"[STARTUP CHECK]   ✔ {csv_name:<20} -> EXISTS")
            else:
                all_found = False
                logger.error(f"[STARTUP CHECK]   ✖ {csv_name:<20} -> MISSING from '{data_dir}'")

        if all_found:
            logger.info(f"[STARTUP CHECK] SUCCESS: All 5 required CSV files verified ready for ingestion.")
        else:
            logger.warning(f"[STARTUP CHECK WARNING] Some required CSV files are missing in '{data_dir}'!")

        logger.info(f"======================================================================")
        return all_found, data_dir, csv_status

    except Exception as e:
        logger.error(f"[STARTUP CHECK CRITICAL ERROR] Failed to resolve synthetic data directory: {e}")
        return False, "", {f: False for f in REQUIRED_CSV_FILES}
