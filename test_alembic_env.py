#!/usr/bin/env python
"""Test script to verify alembic env.py can load target_metadata"""
import sys
sys.path.insert(0, '/app')

print("Step 1: Loading env.py...")
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("env", "/app/migrations/env.py")
    env = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(env)
    print(f"Step 2: env.py loaded successfully")
    print(f"Step 3: target_metadata = {env.target_metadata}")
    print(f"Step 4: target_metadata is None? {env.target_metadata is None}")
    if env.target_metadata is not None:
        print(f"Step 5: target_metadata tables = {list(env.target_metadata.tables.keys())}")
        print("✓ SUCCESS: target_metadata properly loaded!")
    else:
        print("✗ FAIL: target_metadata is None")
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
