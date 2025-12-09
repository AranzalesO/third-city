"""
Quick test script to verify brand detection logic
Run this to debug brand detection issues without running full analysis
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config_manager import ConfigManager
from analyzer import BrandAnalyzer

def test_brand_detection(query):
    """Test brand detection for a specific query"""
    # Load config
    config = ConfigManager()

    # Create analyzer
    analyzer = BrandAnalyzer(config)

    print("="*80)
    print("BRAND DETECTION TEST")
    print("="*80)
    print(f"\nTest Query: '{query}'")
    print(f"\nTarget Brand: {config.get_target_brand()}")
    print(f"Competitors: {config.get_competitors()}")
    print(f"\nAll Brands: {analyzer.all_brands}")
    print(f"Brand Aliases: {analyzer.brand_aliases}")

    # Test brand identification
    query_brands = analyzer.identify_query_brands(query)

    print("\n" + "="*80)
    print("DETECTION RESULTS")
    print("="*80)
    print(f"\nQuery Brands Detected: {query_brands}")
    print(f"Number of brands detected: {len(query_brands)}")

    # Manual verification
    print("\n" + "="*80)
    print("MANUAL VERIFICATION")
    print("="*80)
    query_lower = query.lower()
    print(f"\nQuery (lowercase): '{query_lower}'")

    for brand in analyzer.all_brands:
        brand_lower = brand.lower()
        found = brand_lower in query_lower
        status = "[FOUND]" if found else "[ --- ]"
        print(f"  {status} '{brand}' -> '{brand_lower}'")


if __name__ == "__main__":
    # Default test query
    default_query = "Is GRIDSERVE or ionity better?"

    # Allow custom query via command line
    if len(sys.argv) > 1:
        test_query = " ".join(sys.argv[1:])
    else:
        test_query = default_query

    test_brand_detection(test_query)
