#!/usr/bin/env python3
"""
Display statistics for JSON cache files.

This script analyzes cache files in the data/cache directory and shows:
- Total URLs per cache file
- Status breakdown (success/failed/pending)
- Aggregate totals across all cache files
"""

import json
from pathlib import Path


def get_cache_stats(cache_file_path):
    """Extract statistics from a single cache file."""
    with open(cache_file_path) as f:
        data = json.load(f)

    total = len(data)
    success = sum(1 for v in data.values() if v.get('status') == 'success')
    failed = sum(1 for v in data.values() if v.get('status') == 'failed')
    pending = sum(1 for v in data.values() if v.get('status') == 'pending')

    return {
        'total': total,
        'success': success,
        'failed': failed,
        'pending': pending
    }


def main():
    """Display cache statistics for all JSON files."""
    cache_dir = Path('data/cache')
    cache_files = sorted(cache_dir.glob('*.json'))

    if not cache_files:
        print("No cache files found in data/cache/")
        return

    # Accumulate totals
    totals = {'total': 0, 'success': 0, 'failed': 0, 'pending': 0}

    # Display stats for each file
    for cache_file in cache_files:
        stats = get_cache_stats(cache_file)

        print(f"{cache_file.name}:")
        print(f"  Total: {stats['total']:5d} | Success: {stats['success']:5d} | "
              f"Failed: {stats['failed']:4d} | Pending: {stats['pending']:4d}")
        print()

        # Accumulate totals
        for key in totals:
            totals[key] += stats[key]

    # Display totals
    print("=" * 70)
    print("TOTALS:")
    print(f"  Total: {totals['total']:5d} | Success: {totals['success']:5d} | "
          f"Failed: {totals['failed']:4d} | Pending: {totals['pending']:4d}")


if __name__ == '__main__':
    main()
