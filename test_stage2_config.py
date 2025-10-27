"""Test configuration manager"""

from src.config_manager import ConfigManager

def test_config_manager():
    print("Testing Configuration Manager...")
    print("=" * 60)
    
    # Load config
    config = ConfigManager()
    
    print(config)
    
    print("\nTarget Brand:", config.get_target_brand())
    print("Competitors:", config.get_competitors())
    print("All Brands:", config.get_all_brands())
    print("\nBrand Aliases:")
    for brand, aliases in config.get_brand_aliases().items():
        print(f"  {brand}: {aliases}")
    
    print("\nKeywords:")
    for category, keywords in config.get_keywords().items():
        print(f"  {category}: {keywords[:3]}...")
    
    print("\nRuns per query:", config.get_runs_per_query())
    print("Enabled platforms:", config.get_enabled_platforms())
    
    print("\n✅ Configuration Manager working!")

if __name__ == "__main__":
    test_config_manager()