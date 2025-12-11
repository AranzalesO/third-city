"""
Model Normalizer - Normalizes product model/style names for any brand
"""

from typing import List, Dict
import re


class ModelNormalizer:
    """Normalizes product model and style names for any brand"""

    def __init__(self, brand_models=None):
        """
        Initialize ModelNormalizer with brand-specific models

        Args:
            brand_models: Either:
                         - Dictionary mapping brand names to lists of their models
                           e.g., {"Dr Martens": ["Blaire", "Gryphon", "1460"], ...}
                         - List of models (legacy format, will use "default" as brand)
                         - None (will use empty dict)
        """
        # Handle different input formats
        if brand_models is None:
            self.brand_models = {}
        elif isinstance(brand_models, dict):
            self.brand_models = brand_models
        elif isinstance(brand_models, list):
            # Legacy format: convert list to dict with "default" brand
            self.brand_models = {"default": brand_models}
        else:
            self.brand_models = {}

        # Build variations for each model (add common suffixes)
        self.model_variations = {}
        for brand, models in self.brand_models.items():
            # Ensure models is a list
            if not isinstance(models, list):
                continue

            for model in models:
                # Create variations with common product suffixes
                base_model = model.lower().strip()
                variations = [
                    base_model,
                    f"{base_model} sandal",
                    f"{base_model} sandals",
                    f"{base_model} boot",
                    f"{base_model} boots",
                    f"{base_model} shoe",
                    f"{base_model} shoes",
                ]
                # Store mapping: (brand, variation) -> normalized_model
                for variation in variations:
                    self.model_variations[(brand, variation)] = model

    def normalize_model(self, model_text: str, brand: str = None) -> str:
        """
        Normalize a model name to its canonical form

        Args:
            model_text: The model name to normalize
            brand: Optional brand name to narrow the search

        Returns:
            Normalized model name or None if not found
        """
        model_lower = model_text.lower().strip()

        # If brand specified, only check that brand's models
        if brand:
            if (brand, model_lower) in self.model_variations:
                return self.model_variations[(brand, model_lower)]

            # Partial match for the specified brand
            for (b, variation), normalized in self.model_variations.items():
                if b == brand and (variation in model_lower or model_lower in variation):
                    return normalized
        else:
            # Check all brands
            for (b, variation), normalized in self.model_variations.items():
                if variation == model_lower:
                    return normalized

            # Partial match across all brands
            for (b, variation), normalized in self.model_variations.items():
                if variation in model_lower or model_lower in variation:
                    return normalized

        return None

    def extract_and_normalize_models(self, text: str, brand: str = None) -> List[str]:
        """
        Extract and normalize model names from text

        Args:
            text: The text to extract models from
            brand: Optional brand name to narrow the search

        Returns:
            List of normalized model names found in the text
        """
        text_lower = text.lower()
        found_models = set()

        # Check models for all brands (or specific brand if provided)
        brands_to_check = [brand] if brand else self.brand_models.keys()

        for brand_name in brands_to_check:
            if brand_name not in self.brand_models:
                continue

            # Check each model variation for this brand
            for (b, variation), normalized in self.model_variations.items():
                if b == brand_name and variation in text_lower:
                    found_models.add(normalized)

        return sorted(list(found_models))
