"""
Brand Analyzer - Core analysis engine
"""

import re
from collections import Counter
from typing import Dict, List, Tuple, Any


class BrandAnalyzer:
    """Analyzes LLM responses for brand mentions, sources, models, and key messages"""
    
    def __init__(self, config_manager):
        self.config = config_manager
        self.all_brands = config_manager.get_all_brands()
        self.brand_aliases = config_manager.get_brand_aliases()
        self.keywords = config_manager.get_keywords()
        self.models = config_manager.get_models()
    
    def identify_query_brands(self, query: str) -> List[str]:
        """Identify which brands are explicitly mentioned in the query"""
        query_lower = query.lower()
        mentioned_brands = []
        
        for brand in self.all_brands:
            # Check main brand name
            if brand.lower() in query_lower:
                mentioned_brands.append(brand)
                continue
            
            # Check aliases
            aliases = self.brand_aliases.get(brand, [])
            if any(alias in query_lower for alias in aliases):
                mentioned_brands.append(brand)
        
        return mentioned_brands
    
    def extract_brands_from_response(self, response: str) -> List[str]:
        """Extract mentioned brands from response text"""
        found_brands = []
        response_lower = response.lower()
        
        for brand in self.all_brands:
            brand_found = False
            
            # Check exact brand name
            if brand.lower() in response_lower:
                brand_found = True
            
            # Check aliases
            if not brand_found:
                aliases = self.brand_aliases.get(brand, [])
                for alias in aliases:
                    if alias in response_lower:
                        brand_found = True
                        break
            
            if brand_found:
                found_brands.append(brand)
        
        return found_brands
    
    def detect_implicit_brand_reference(self, query: str, response: str, 
                                       query_brands: List[str]) -> List[str]:
        """Detect implicit brand references using pronouns"""
        response_lower = response.lower()
        implicit_brands = []
        
        if not query_brands or len(response) < 50:
            return []
        
        # Check if response is unhelpful
        unhelpful_phrases = [
            "i don't know", "i'm not sure", "cannot provide",
            "unable to", "don't have information", "can't say"
        ]
        
        if any(phrase in response_lower for phrase in unhelpful_phrases):
            return []
        
        # Check for pronoun usage
        pronoun_indicators = [
            "they are", "they're", "it is", "it's", "these are",
            "this brand", "the brand", "them"
        ]
        
        has_pronouns = any(pronoun in response_lower for pronoun in pronoun_indicators)
        
        if has_pronouns:
            implicit_brands.extend(query_brands)
        
        return implicit_brands
    
    def extract_sources(self, response: str) -> List[str]:
        """Extract domain names from response"""
        domains = re.findall(
            r'(?:https?://)?(?:www\.)?([A-Za-z0-9\-]+\.[A-Za-z\.]{2,})',
            response.lower()
        )
        
        # Filter artifacts
        filtered = [d for d in domains if d and 'e.g' not in d.lower() and len(d) > 4]
        
        return filtered
    
    def extract_models(self, response: str, brand: str = None) -> List[str]:
        """Extract product models/styles from response"""
        models_found = []
        
        # If brand specified, check brand-specific models first
        if brand and brand in self.models:
            brand_models = self.models[brand]
            response_lower = response.lower()
            
            for model in brand_models:
                if model.lower() in response_lower:
                    models_found.append(model)
        
        # Generic model patterns
        patterns = [
            r'\b([A-Z][a-z]+(?:\s[A-Z0-9][a-zA-Z0-9]*)+)',
            r'\b(\d{3,4})\b',
            r'\b([A-Z]{2,}(?:\s\d+)?)\b',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response)
            models_found.extend(matches)
        
        # Filter stop words
        stop_words = [
            'The', 'This', 'That', 'These', 'Those', 'When', 'Where', 'What', 'Which',
            'Sandals', 'Sandal', 'Breaking', 'Walking', 'Summer', 'Style', 'Styles',
            'UK', 'ASOS', 'Amazon', 'Official', 'Website', 'Comfort', 'Quality',
            'Support', 'Durability', 'Value', 'Price', 'Point', 'Options', 'Strap',
            'Technology', 'PVC', 'Width', 'Edgy', 'Major', 'High', 'Street', 'Brands'
        ]
        
        models_found = [m.strip() for m in models_found 
                       if m.strip() and m not in stop_words and len(m.strip()) > 1]
        
        # Filter years
        models_found = [m for m in models_found 
                       if not (m.isdigit() and len(m) == 4 and 2020 <= int(m) <= 2030)]
        
        return list(set(models_found))
    
    def detect_key_messages(self, response: str) -> Dict[str, bool]:
        """Detect which key messages are present"""
        response_lower = response.lower()
        detected = {}
        
        for category, keywords in self.keywords.items():
            detected[category] = any(kw in response_lower for kw in keywords)
        
        return detected
    
    def analyze_single_response(self, query: str, response: str, 
                               query_brands: List[str]) -> Dict[str, Any]:
        """Analyze a single response"""
        # Extract brands
        explicit_brands = self.extract_brands_from_response(response)
        implicit_brands = self.detect_implicit_brand_reference(query, response, query_brands)
        all_brands = list(set(explicit_brands + implicit_brands))
        
        # Extract other data
        sources = self.extract_sources(response)
        models = self.extract_models(response)
        key_messages = self.detect_key_messages(response)
        
        return {
            'brands': all_brands,
            'sources': sources,
            'models': models,
            'key_messages': key_messages
        }
    
    def aggregate_results(self, query: str, results: List[Dict[str, Any]], 
                         total_runs: int) -> Dict[str, Any]:
        """Aggregate results from multiple runs"""
        query_brands = self.identify_query_brands(query)
        
        # Aggregate brands
        all_brands_seen = []
        for result in results:
            all_brands_seen.extend(result['brands'])
        
        brand_counter = Counter(all_brands_seen)
        
        # Separate query brands from organic
        query_brand_stats = []
        for qb in query_brands:
            count = brand_counter.get(qb, 0)
            likelihood = round((count / total_runs) * 100) if total_runs > 0 else 0
            query_brand_stats.append((qb, likelihood))
        
        # Organic competitors
        organic_competitors = {brand: count for brand, count in brand_counter.items()
                              if brand not in query_brands}
        organic_top = Counter(organic_competitors).most_common(3)
        
        # Aggregate sources
        all_sources = []
        for result in results:
            all_sources.extend(result['sources'])
        source_counter = Counter(all_sources)
        top_sources = source_counter.most_common(5)
        
        # Aggregate models
        all_models = []
        for result in results:
            all_models.extend(result['models'])
        model_counter = Counter(all_models)
        top_models = model_counter.most_common(5)
        
        # Aggregate key messages
        key_message_counts = {cat: 0 for cat in self.keywords.keys()}
        for result in results:
            for category, detected in result['key_messages'].items():
                if detected:
                    key_message_counts[category] += 1
        
        return {
            'query': query,
            'query_brands': query_brand_stats,
            'organic_competitors': organic_top,
            'sources': top_sources,
            'models': top_models,
            'key_messages': key_message_counts,
            'total_runs': total_runs
        }