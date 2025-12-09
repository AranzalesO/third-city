"""
Test what happens if required fields are empty
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config_manager import ConfigManager

def test_empty_target_brand():
    """Test validation with empty target brand"""

    # Create test config with empty target_brand
    test_config = {
        'campaign_name': 'Test Campaign',
        'target_brand': '',  # EMPTY!
        'competitors': ['Competitor1', 'Competitor2'],
        'runs_per_query': 10,
        'platforms': {
            'chatgpt': True,
            'gemini': True,
            'perplexity': True
        }
    }

    print("="*80)
    print("TEST: Empty Target Brand")
    print("="*80)
    print(f"\nTest Config:")
    print(f"  campaign_name: '{test_config['campaign_name']}'")
    print(f"  target_brand: '{test_config['target_brand']}'  ← EMPTY STRING")
    print(f"  competitors: {test_config['competitors']}")

    # Try to validate
    print("\nTesting validation...")
    config_manager = ConfigManager.__new__(ConfigManager)
    config_manager.config = test_config

    try:
        config_manager.validate_config(test_config)
        print("✓ Validation PASSED (no error thrown)")
        print("\n⚠ WARNING: Empty target_brand passed validation!")
        print("This could cause errors during analysis.")

        # Test what methods return
        print("\nTesting get methods:")
        print(f"  get_target_brand() = '{config_manager.get_target_brand()}'")
        print(f"  get_all_brands() = {config_manager.get_all_brands()}")

    except ValueError as e:
        print(f"✗ Validation FAILED with error: {e}")
        print("\n✓ Good! Empty target_brand was caught.")


def test_missing_target_brand():
    """Test validation with missing target_brand field"""

    # Create test config WITHOUT target_brand field
    test_config = {
        'campaign_name': 'Test Campaign',
        # 'target_brand' is MISSING entirely
        'competitors': ['Competitor1', 'Competitor2'],
        'runs_per_query': 10,
        'platforms': {
            'chatgpt': True,
            'gemini': True,
            'perplexity': True
        }
    }

    print("\n" + "="*80)
    print("TEST: Missing Target Brand Field")
    print("="*80)
    print(f"\nTest Config (target_brand field missing):")
    print(f"  campaign_name: '{test_config['campaign_name']}'")
    print(f"  target_brand: <missing>")
    print(f"  competitors: {test_config['competitors']}")

    # Try to validate
    print("\nTesting validation...")
    config_manager = ConfigManager.__new__(ConfigManager)
    config_manager.config = test_config

    try:
        config_manager.validate_config(test_config)
        print("✓ Validation PASSED (no error thrown)")
        print("\n⚠ WARNING: Missing target_brand field passed validation!")

    except ValueError as e:
        print(f"✗ Validation FAILED with error: {e}")
        print("\n✓ Good! Missing target_brand field was caught.")


if __name__ == "__main__":
    test_empty_target_brand()
    test_missing_target_brand()

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("""
The current validation:
- ✓ Catches MISSING fields (raises ValueError)
- ✗ Does NOT catch EMPTY strings

Recommendation:
- Web form has HTML 'required' attribute → Browser blocks submission
- Web form has server-side check (line 154 in web_app.py) → Blocks empty strings
- Direct config.json editing could bypass validation!
    """)
