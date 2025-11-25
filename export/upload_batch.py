#!/usr/bin/env python3
"""Batch upload forecast JSON files to basinwx.com.

Uploads all JSON files from a directory to the BasinWx API.
Requires DATA_UPLOAD_API_KEY environment variable.

Usage:
    python upload_batch.py --json-dir /path/to/json/files
    python upload_batch.py --json-dir /scratch/general/vast/clyfar_test/json/2025112400

Created: 2025-11-25
"""
import argparse
import os
import sys
from pathlib import Path

# Add parent dir for imports if running as script
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from brc_tools.download.push_data import send_json_to_server
except ImportError:
    print("Error: brc_tools not found. Install with: pip install -e /path/to/brc-tools")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Batch upload forecast JSON to BasinWx")
    parser.add_argument('--json-dir', required=True, help="Directory containing JSON files")
    parser.add_argument('--data-type', default='forecasts', help="API data type (default: forecasts)")
    parser.add_argument('--server', default='https://basinwx.com', help="Server URL")
    parser.add_argument('--dry-run', action='store_true', help="List files without uploading")
    args = parser.parse_args()

    # Check API key
    api_key = os.environ.get('DATA_UPLOAD_API_KEY')
    if not api_key and not args.dry_run:
        print("Error: DATA_UPLOAD_API_KEY environment variable not set")
        sys.exit(1)

    json_dir = Path(args.json_dir)
    if not json_dir.exists():
        print(f"Error: Directory not found: {json_dir}")
        sys.exit(1)

    files = sorted(json_dir.glob('*.json'))
    if not files:
        print(f"No JSON files found in {json_dir}")
        sys.exit(1)

    print(f"Found {len(files)} JSON files in {json_dir}")

    if args.dry_run:
        print("\nDry run - would upload:")
        for f in files:
            print(f"  {f.name}")
        return

    print(f"Uploading to {args.server}/api/upload/{args.data_type}...\n")

    success = 0
    failed = 0

    for f in files:
        try:
            send_json_to_server(
                server_address=args.server,
                fpath=str(f),
                file_data=args.data_type,
                API_KEY=api_key
            )
            success += 1
        except Exception as e:
            print(f"  Error uploading {f.name}: {e}")
            failed += 1

    print(f"\nDone. {success} uploaded, {failed} failed.")


if __name__ == '__main__':
    main()
