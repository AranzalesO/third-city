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
        """Extract mentioned brands from response text - PRESERVING ORDER"""
        brand_positions = []
        
        for brand in self.all_brands:
            # Find first occurrence of brand name
            pos = response.lower().find(brand.lower())
            if pos != -1:
                brand_positions.append((pos, brand))
                continue
            
            # Check aliases
            aliases = self.brand_aliases.get(brand, [])
            for alias in aliases:
                pos = response.lower().find(alias.lower())
                if pos != -1:
                    brand_positions.append((pos, brand))
                    break
        
        # Sort by position (earliest first) and remove duplicates
        brand_positions.sort(key=lambda x: x[0])
        
        # Build ordered list without duplicates
        found_brands = []
        seen = set()
        for _, brand in brand_positions:
            if brand not in seen:
                found_brands.append(brand)
                seen.add(brand)
        
        return found_brands
    
    def extract_brands_from_domains(self, domains: List[str]) -> List[str]:
        """Extract brand names from domain URLs"""
        found_brands = []
        
        for domain in domains:
            domain_lower = domain.lower()
            
            # Check each brand against the domain
            for brand in self.all_brands:
                brand_lower = brand.lower().replace(' ', '').replace('-', '')
                
                # Check if brand name is in domain (e.g., gridserve in gridserve.com)
                if brand_lower in domain_lower.replace('.', '').replace('-', ''):
                    if brand not in found_brands:
                        found_brands.append(brand)
                    continue
                
                # Check aliases
                aliases = self.brand_aliases.get(brand, [])
                for alias in aliases:
                    alias_clean = alias.lower().replace(' ', '').replace('-', '')
                    if alias_clean in domain_lower.replace('.', '').replace('-', ''):
                        if brand not in found_brands:
                            found_brands.append(brand)
                        break
        
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
        
        # Generic model patterns - only very specific ones
        patterns = [
            r'\b(\d{4})\b',  # 4-digit numbers only (like 1460, 2976)
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response)
            models_found.extend(matches)
        
        # Comprehensive stop words - filter out false positives
        stop_words = [
            # Generic words
            'The', 'This', 'That', 'These', 'Those', 'When', 'Where', 'What', 'Which',
            'Some', 'Many', 'Most', 'Best', 'Good', 'Great', 'Very', 'More', 'Less',
            
            # Product categories (not specific models)
            'Sandals', 'Sandal', 'Boot', 'Boots', 'Shoe', 'Shoes', 'Footwear',
            'Breaking', 'Walking', 'Summer', 'Winter', 'Spring', 'Style', 'Styles',
            
            # Retailers and websites
            'UK', 'ASOS', 'Amazon', 'Official', 'Website', 'John', 'Lewis', 'Schuh',
            'Office', 'Clarks', 'Next', 'Debenhams', 'Selfridges', 'Harrods',
            
            # Attributes (not models)
            'Comfort', 'Quality', 'Support', 'Durability', 'Value', 'Price', 'Point',
            'Options', 'Strap', 'Technology', 'PVC', 'Width', 'Edgy', 'Major', 
            'High', 'Street', 'Brands', 'Leather', 'Vegan', 'Classic', 'Modern',
            
            # Months and temporal
            'January', 'February', 'March', 'April', 'May', 'June', 'July',
            'August', 'September', 'October', 'November', 'December',
            'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
            
            # Generic descriptors
            'Collection', 'Range', 'Series', 'Line', 'Model', 'Version', 'Edition',
            'Platform', 'Chunky', 'Lightweight', 'Heavy', 'Durable', 'Comfortable'
        ]
        
        # Filter models
        filtered_models = []
        for model in models_found:
            model_clean = model.strip()
            
            # Skip if empty or too short
            if not model_clean or len(model_clean) <= 1:
                continue
            
            # Skip if in stop words (case insensitive)
            if model_clean in stop_words or model_clean.lower() in [s.lower() for s in stop_words]:
                continue
            
            # Skip years (2020-2030)
            if model_clean.isdigit() and len(model_clean) == 4:
                year = int(model_clean)
                if 2020 <= year <= 2030:
                    continue
            
            # Skip if it contains "UK" or other common suffixes
            if any(suffix in model_clean for suffix in ['UK', 'US', 'EU', ' Ltd', ' Inc']):
                continue
            
            # Skip if it looks like a date pattern
            if re.match(r'\d{1,2}[/-]\d{1,2}', model_clean):
                continue
            
            filtered_models.append(model_clean)
        
        return list(set(filtered_models))
    
    def detect_key_messages(self, response: str) -> Dict[str, bool]:
        """Detect which key messages are present"""
        response_lower = response.lower()
        detected = {}
        
        for category, keywords in self.keywords.items():
            detected[category] = any(kw.lower() in response_lower for kw in keywords)
        
        return detected
    
    def detect_sentiment(self, response: str) -> str:
        """Detect sentiment/tone: POS (Positive), NEG (Negative), NEU (Neutral)"""
        response_lower = response.lower()

        # Positive indicators
        positive_words = [
            "excellent", "great", "good", "best", "high quality", "comfortable",
            "reliable", "recommended", "love", "perfect", "amazing", "fantastic",
            "outstanding", "superior", "impressive"
        ]

        # Negative indicators
        negative_words = [
            "poor", "bad", "worst", "uncomfortable", "unreliable", "avoid",
            "disappointed", "terrible", "awful", "waste", "regret", "inferior",
            "subpar", "lacking"
        ]

        positive_count = sum(1 for word in positive_words if word in response_lower)
        negative_count = sum(1 for word in negative_words if word in response_lower)

        if positive_count > negative_count and positive_count > 0:
            return "POS"
        elif negative_count > positive_count and negative_count > 0:
            return "NEG"
        else:
            return "NEU"  # Neutral
    
    def analyze_single_response(self, query: str, response: str, 
                               query_brands: List[str]) -> Dict[str, Any]:
        """Analyze a single response"""
        # Extract sources first
        sources = self.extract_sources(response)
        
        # Extract brands from text IN ORDER
        explicit_brands = self.extract_brands_from_response(response)
        
        # Extract brands from domains
        domain_brands = self.extract_brands_from_domains(sources)
        
        # Combine - explicit brands FIRST (they preserve order), then add domain brands
        all_brands = explicit_brands.copy()
        for brand in domain_brands:
            if brand not in all_brands:
                all_brands.append(brand)
        
        # Detect implicit brand references
        implicit_brands = self.detect_implicit_brand_reference(query, response, query_brands)
        for brand in implicit_brands:
            if brand not in all_brands:
                all_brands.append(brand)
        
        # Extract other data
        models = self.extract_models(response)
        key_messages = self.detect_key_messages(response)
        sentiment = self.detect_sentiment(response)
        
        return {
            'brands': all_brands,  # NOW IN ORDER!
            'sources': sources,
            'models': models,
            'key_messages': key_messages,
            'sentiment': sentiment
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
        
        # Aggregate key messages - CONVERT TO PERCENTAGES
        key_message_counts = {cat: 0 for cat in self.keywords.keys()}
        for result in results:
            for category, detected in result['key_messages'].items():
                if detected:
                    key_message_counts[category] += 1
        
        # Convert counts to percentages
        key_message_percentages = {}
        for category, count in key_message_counts.items():
            percentage = round((count / total_runs) * 100) if total_runs > 0 else 0
            key_message_percentages[category] = percentage
        
        return {
            'query': query,
            'query_brands': query_brand_stats,
            'organic_competitors': organic_top,
            'sources': top_sources,
            'models': top_models,
            'key_messages': key_message_percentages,  # Returns percentages now
            'total_runs': total_runs
        }