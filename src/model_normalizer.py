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
            "1460": ["1460", "1460 boot", "1460 sandal"],
            "2976": ["2976", "2976 boot"],
            "1461": ["1461", "1461 shoe"],
        }
        
        # Create reverse lookup
        self.variation_to_normalized = {}
        for normalized, variations in self.dr_martens_sandals.items():
            for variant in variations:
                self.variation_to_normalized[variant.lower()] = normalized
    
    def normalize_model(self, model_text: str) -> str:
        """Normalize a model name to its canonical form"""
        model_lower = model_text.lower().strip()
        
        # Direct lookup
        if model_lower in self.variation_to_normalized:
            return self.variation_to_normalized[model_lower]
        
        # Partial match
        for variant, normalized in self.variation_to_normalized.items():
            if variant in model_lower or model_lower in variant:
                return normalized
        
        # No match found, return original
        return model_text
    
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
        
        # Also try generic pattern matching
        generic_models = self._extract_generic_models(text)
        for model in generic_models:
            normalized = self.normalize_model(model)
            if normalized:
                found_models.add(normalized)
        
        return sorted(list(found_models))
    
    def _extract_generic_models(self, text: str) -> List[str]:
        """Extract potential model names using patterns"""
        patterns = [
            r'\b([A-Z][a-z]+)\s+(?:Sandal|Boot|Shoe)s?\b',  # "Blaire Sandals"
            r'\b\d{4}\b',  # 4-digit models like "1460"
        ]
        
        models = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            models.extend(matches)
        
        # Filter stop words
        stop_words = ['Summer', 'Style', 'Walking', 'These', 'Those']
        models = [m for m in models if m not in stop_words]
        
        return models