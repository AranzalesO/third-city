"""
Model Normalizer - Normalizes product model/style names
"""

from typing import List, Dict
import re


class ModelNormalizer:
    """Normalizes product model and style names"""
    
    def __init__(self):
        # Dr Martens Sandal Styles - from Sandal Styles.xlsx
        self.dr_martens_sandals = {
            # Normalized name: [variations, aliases]
            "Blaire": ["blaire", "blair", "blaire sandal", "blaire sandals"],
            "Clarissa": ["clarissa", "clarissa sandal", "clarissa sandals"],
            "Gryphon": ["gryphon", "gryphon sandal", "gryphon sandals"],
            "Voss": ["voss", "voss sandal", "voss sandals"],
            "Terry": ["terry", "terry sandal", "terry sandals"],
            "Myles": ["myles", "myle", "myles sandal", "myles sandals"],
            "Nartilla": ["nartilla", "nartilla sandal", "nartilla sandals"],
            "Kimber": ["kimber", "kimber sandal", "kimber sandals"],
            "Shore": ["shore", "shore sandal", "shore gladiator", "shore reinvented"],
            "Romi": ["romi", "romi sandal", "romi sandals"],
            "Hayden": ["hayden", "hayden sandal", "hayden sandals"],
            "Jude": ["jude", "jude sandal", "jude sandals"],
            "Vegan Blaire": ["vegan blaire", "blaire vegan"],
            "Vegan Gryphon": ["vegan gryphon", "gryphon vegan"],
            "Vegan Myles": ["vegan myles", "myles vegan"],
            "Vegan Clarissa": ["vegan clarissa", "clarissa vegan"],
            
            # Numeric models
            "1460": ["1460", "1460 boot"],
            "2976": ["2976", "2976 boot"],
            "1461": ["1461", "1461 shoe"],
        }
        
        # Create reverse lookup
        self.variation_to_normalized = {}
        for normalized, variations in self.dr_martens_sandals.items():
            for variant in variations:
                self.variation_to_normalized[variant.lower()] = normalized
        
        # Valid numeric models (4-digit codes)
        self.valid_numeric_models = {"1460", "2976", "1461", "8053", "1490"}
    
    def normalize_model(self, model_text: str) -> str:
        """Normalize a model name to its canonical form"""
        model_lower = model_text.lower().strip()
        
        # Direct lookup
        if model_lower in self.variation_to_normalized:
            return self.variation_to_normalized[model_lower]
        
        # Check if it's a valid numeric model
        if model_text.isdigit() and len(model_text) == 4:
            if model_text in self.valid_numeric_models:
                return model_text
            else:
                # Unknown 4-digit code - filter out
                return None
        
        # Partial match for known styles
        for variant, normalized in self.variation_to_normalized.items():
            if variant in model_lower or model_lower in variant:
                return normalized
        
        # No match found - filter out
        return None
    
    def extract_and_normalize_models(self, text: str, brand: str = "Dr Martens") -> List[str]:
        """Extract and normalize model names from text"""
        text_lower = text.lower()
        found_models = set()
        
        # Check each known model
        for normalized, variations in self.dr_martens_sandals.items():
            for variant in variations:
                if variant in text_lower:
                    found_models.add(normalized)
                    break
        
        # Check for valid numeric models
        numeric_models = re.findall(r'\b(\d{4})\b', text)
        for num_model in numeric_models:
            if num_model in self.valid_numeric_models:
                found_models.add(num_model)
        
        return sorted(list(found_models))