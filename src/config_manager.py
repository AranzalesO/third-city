"""
Configuration Manager - Handles loading and validating campaign configurations
"""

import json
import os
from typing import Dict, List, Any


class ConfigManager:
    """Manages campaign configuration"""
    
    def __init__(self, config_path: str = "config/config.json"):
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Validate configuration
        self.validate_config(config)
        
        return config
    
    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate that configuration has all required fields"""
        required_fields = [
            'campaign_name',
            'target_brand',
            'competitors',
            'runs_per_query',
            'platforms'
        ]
        
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field in config: {field}")
        
        # Validate at least one platform is enabled
        if not any(config['platforms'].values()):
            raise ValueError("At least one platform must be enabled")
        
        # Validate runs_per_query
        if config['runs_per_query'] < 1:
            raise ValueError("runs_per_query must be at least 1")
    
    def get_target_brand(self) -> str:
        """Get the target brand name"""
        return self.config['target_brand']
    
    def get_competitors(self) -> List[str]:
        """Get list of competitors"""
        return self.config['competitors']
    
    def get_all_brands(self) -> List[str]:
        """Get list of all brands (target + competitors)"""
        brands = [self.config['target_brand']] + self.config['competitors']
        return list(set(brands))  # Remove duplicates
    
    def get_brand_aliases(self, brand: str = None) -> Dict[str, List[str]]:
        """Get brand aliases dictionary or for specific brand"""
        aliases = self.config.get('brand_aliases', {})
        
        if brand:
            return aliases.get(brand, [brand.lower()])
        
        return aliases
    
    def get_models(self, brand: str = None) -> Dict[str, List[str]]:
        """Get model lists"""
        models = self.config.get('models', {})
        
        if brand:
            return models.get(brand, [])
        
        return models
    
    def get_keywords(self) -> Dict[str, List[str]]:
        """Get keyword categories"""
        return self.config.get('keywords', {})
    
    def get_queries(self) -> List[str]:
        """Get list of queries"""
        return self.config.get('queries', [])
    
    def load_queries_from_file(self, filepath: str) -> List[str]:
        """Load queries from a text file (one per line)"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Queries file not found: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            queries = [line.strip() for line in f.readlines() if line.strip()]
        
        # Filter out comments and metadata lines
        queries = [q for q in queries if not q.startswith('#') 
                   and not q.lower().startswith('brand:')
                   and not q.lower().startswith('competitors:')]
        
        return queries
    
    def get_runs_per_query(self) -> int:
        """Get number of runs per query"""
        return self.config['runs_per_query']
    
    def get_enabled_platforms(self) -> List[str]:
        """Get list of enabled platforms"""
        platforms = self.config['platforms']
        return [platform for platform, enabled in platforms.items() if enabled]
    
    def get_system_prompt(self) -> str:
        """Get system prompt"""
        return self.config.get('system_prompt', 
                              "Answer as a UK consumer searching online. Keep answers factual and neutral.")
    
    def get_campaign_name(self) -> str:
        """Get campaign name"""
        return self.config.get('campaign_name', 'Brand Monitoring Campaign')
    
    def save_config(self, config: Dict[str, Any] = None) -> None:
        """Save configuration to file"""
        if config:
            self.config = config
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def update_queries(self, queries: List[str]) -> None:
        """Update queries in configuration"""
        self.config['queries'] = queries
        self.save_config()
    
    def __str__(self) -> str:
        """String representation of config"""
        return f"""
Campaign: {self.get_campaign_name()}
Target Brand: {self.get_target_brand()}
Competitors: {len(self.get_competitors())}
Queries: {len(self.get_queries())}
Runs per Query: {self.get_runs_per_query()}
Platforms: {', '.join(self.get_enabled_platforms())}
"""