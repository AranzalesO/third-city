# src/query_processor.py
"""
Query Processor - Orchestrates query execution across platforms
"""

import time
import random
import re
import json
import os
from datetime import datetime
from typing import List, Dict, Any
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from api_clients import LLMClientFactory
from analyzer import BrandAnalyzer
from config_manager import ConfigManager
from model_normalizer import ModelNormalizer


class QueryProcessor:
    """Processes queries across multiple LLM platforms"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.analyzer = BrandAnalyzer(config_manager)
        self.model_normalizer = ModelNormalizer()
        self.clients = self._initialize_clients()
        self.system_prompt = config_manager.get_system_prompt()
    
    def _initialize_clients(self):
        """Initialize LLM clients for enabled platforms"""
        clients = {}
        enabled_platforms = self.config.get_enabled_platforms()
        
        for platform in enabled_platforms:
            try:
                client = LLMClientFactory.create_client(platform)
                clients[client.get_platform_name()] = client
                print(f"✓ {client.get_platform_name()} initialized")
            except Exception as e:
                print(f"✗ Failed to initialize {platform}: {e}")
        
        if not clients:
            raise ValueError("No LLM clients could be initialized")
        
        return clients
    
    def process_single_query_run(self, query: str, client, query_brands: List[str]) -> Dict[str, Any]:
        """Process a single run of a query on a specific platform"""
        platform = client.get_platform_name()
        
        try:
            # Add source request to query
            full_query = f"{query}\n\nIMPORTANT: List all website URLs or domain names you referenced to answer this question."
            
            # Query the platform
            response = client.query(full_query, self.system_prompt)
            
            # Check if response is valid
            if not response or len(response) < 10:
                return {
                    'brands': [],
                    'sources': [],
                    'models': [],
                    'key_messages': {},
                    'sentiment': 'N',
                    'platform': platform,
                    'success': False,
                    'error': 'Empty or invalid response'
                }
            
            # Analyze response
            analysis = self.analyzer.analyze_single_response(query, response, query_brands)
            
            # Normalize models - use comprehensive normalizer only
            additional_models = self.model_normalizer.extract_and_normalize_models(response)
            
            analysis['models'] = list(set(additional_models))
            analysis['platform'] = platform
            analysis['success'] = True
            
            return analysis
            
        except Exception as e:
            error_msg = str(e)[:100]
            return {
                'brands': [],
                'sources': [],
                'models': [],
                'key_messages': {},
                'sentiment': 'N',
                'platform': platform,
                'success': False,
                'error': error_msg
            }
    
    def process_query_on_platform(self, query: str, platform_name: str, 
                                   runs: int = 5) -> Dict[str, Any]:
        """Process a single query multiple times on a specific platform"""
        client = self.clients[platform_name]
        query_brands = self.analyzer.identify_query_brands(query)
        
        results = []
        successful_runs = 0
        failed_runs = 0
        
        platform_start = time.time()
        print(f"    {platform_name}: ", end="", flush=True)
        
        for run in range(runs):
            result = self.process_single_query_run(query, client, query_brands)
            results.append(result)
            
            if result['success']:
                successful_runs += 1
                # Only print progress every 5 runs to reduce console spam
                if (run + 1) % 5 == 0 or run == runs - 1:
                    print(f"✓", end="", flush=True)
            else:
                failed_runs += 1
                if failed_runs <= 3:  # Only show first 3 failures
                    print("✗", end="", flush=True)
            
            # Reduced rate limiting - faster processing
            if run < runs - 1:  # Don't sleep after last run
                time.sleep(random.uniform(0.2, 0.5))
        
        platform_time = time.time() - platform_start
        print(f" ({successful_runs}/{runs}) [{platform_time:.1f}s]", flush=True)
        
        # Aggregate results for this platform
        aggregated = self._aggregate_platform_results(query, results, query_brands, successful_runs)
        aggregated['platform'] = platform_name
        
        return aggregated
    
    def _aggregate_platform_results(self, query: str, results: List[Dict], 
                                    query_brands: List[str], total_runs: int) -> Dict[str, Any]:
        """Aggregate results from multiple runs on same platform"""
        # Collect all data
        all_brands = []
        all_sources = []
        all_models = []
        key_messages_count = {}
        brand_positions = []
        sentiment_scores = []
        
        for result in results:
            if not result['success']:
                continue
            
            all_brands.extend(result['brands'])
            all_sources.extend(result['sources'])
            all_models.extend(result['models'])
            
            # Track key messages
            for category, detected in result['key_messages'].items():
                if category not in key_messages_count:
                    key_messages_count[category] = 0
                if detected:
                    key_messages_count[category] += 1
            
            # Track position
            if query_brands:
                query_brand = query_brands[0]
                if query_brand in result['brands']:
                    position = result['brands'].index(query_brand) + 1
                    brand_positions.append(position)
            
            # Track sentiment
            if 'sentiment' in result:
                sentiment_scores.append(result['sentiment'])
        
        # Aggregate brands
        brand_counter = Counter(all_brands)
        
        # Query brand stats
        query_brand_stats = []
        for qb in query_brands:
            count = brand_counter.get(qb, 0)
            likelihood = round((count / total_runs) * 100) if total_runs > 0 else 0
            query_brand_stats.append((qb, likelihood))
        
        # Organic competitors
        organic_competitors = {brand: count for brand, count in brand_counter.items()
                              if brand not in query_brands}
        organic_top = Counter(organic_competitors).most_common(3)
        
        # All competitors mentioned (comma-separated)
        all_competitors = [brand for brand, count in brand_counter.most_common(10) 
                          if brand not in query_brands]
        all_competitors_str = ", ".join(all_competitors) if all_competitors else ""
        
        # Position
        position_str = ""
        if brand_positions:
            most_common_position = Counter(brand_positions).most_common(1)[0][0]
            position_map = {1: "First", 2: "Second", 3: "Third"}
            position_str = position_map.get(most_common_position, f"{most_common_position}th")
        
        # Sources
        source_counter = Counter(all_sources)
        top_sources = source_counter.most_common(5)
        
        # Source recency
        source_recency = self._detect_source_recency(top_sources)
        
        # Models
        model_counter = Counter(all_models)
        top_models = model_counter.most_common(10)
        
        # Key message percentages
        key_message_percentages = {}
        for category, count in key_messages_count.items():
            percentage = round((count / total_runs) * 100) if total_runs > 0 else 0
            key_message_percentages[category] = percentage
        
        # Tone
        tone = self._determine_tone(sentiment_scores)
        
        # Timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return {
            'query': query,
            'query_brands': query_brand_stats,
            'organic_competitors': organic_top,
            'all_competitors_mentioned': all_competitors_str,
            'position': position_str,
            'sources': top_sources,
            'source_recency': source_recency,
            'models': top_models,
            'key_messages': key_message_percentages,
            'tone': tone,
            'timestamp': timestamp,
            'total_runs': total_runs
        }
    
    def _detect_source_recency(self, sources: List[tuple]) -> str:
        """Detect recency from source URLs"""
        current_year = datetime.now().year
        
        for source, count in sources:
            # Look for year patterns in URL
            year_match = re.search(r'(20\d{2})', source)
            if year_match:
                year = int(year_match.group(1))
                if year == current_year:
                    return f"{current_year} (Current)"
                elif year >= current_year - 1:
                    return f"{year} (Recent)"
                else:
                    return f"{year}"
        
        return "Unknown"
    
    def _determine_tone(self, sentiment_scores: List[str]) -> str:
        """Determine overall tone from sentiment scores"""
        if not sentiment_scores:
            return "N"  # Neutral
        
        most_common = Counter(sentiment_scores).most_common(1)[0][0]
        return most_common  # "P", "N", or "N"
    
    def _save_checkpoint(self, checkpoint_file: str, platform_results: Dict, 
                        last_completed: int):
        """Save progress checkpoint"""
        try:
            os.makedirs("output", exist_ok=True)
            with open(checkpoint_file, 'w') as f:
                json.dump({
                    'last_completed_query': last_completed,
                    'results': platform_results,
                    'timestamp': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            print(f"\n⚠ Warning: Could not save checkpoint: {e}")
    
    def _load_checkpoint(self, checkpoint_file: str) -> tuple:
        """Load progress checkpoint"""
        if not os.path.exists(checkpoint_file):
            return None, 0
        
        try:
            with open(checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
                platform_results = checkpoint.get('results', None)
                start_query = checkpoint.get('last_completed_query', 0)
                timestamp = checkpoint.get('timestamp', 'unknown')
                
                print(f"\n📂 Found checkpoint from {timestamp}")
                print(f"   Resuming from query {start_query + 1}")
                
                return platform_results, start_query
        except Exception as e:
            print(f"\n⚠ Warning: Could not load checkpoint: {e}")
            return None, 0
    
    def process_all_queries(self, queries: List[str], progress_callback=None) -> Dict[str, List[Dict[str, Any]]]:
        """Process all queries across all platforms - returns results per platform"""
        total_queries = len(queries)
        runs_per_query = self.config.get_runs_per_query()
        
        # Checkpoint setup
        checkpoint_file = "output/checkpoint.json"
        
        # Try to load checkpoint
        loaded_results, start_query = self._load_checkpoint(checkpoint_file)
        
        if loaded_results:
            platform_results = loaded_results
        else:
            platform_results = {platform: [] for platform in self.clients.keys()}
        
        print("\n" + "=" * 80)
        print(f"PROCESSING {total_queries} QUERIES")
        print(f"Runs per query per platform: {runs_per_query}")
        print(f"Platforms: {', '.join(self.clients.keys())}")
        print(f"Total API calls: {total_queries * runs_per_query * len(self.clients)}")
        print(f"⚡ PARALLEL MODE: Processing all platforms simultaneously")
        if start_query > 0:
            print(f"Starting from query: {start_query + 1}/{total_queries}")
        print("=" * 80)
        
        start_time = datetime.now()
        
        try:
            for idx in range(start_query, total_queries):
                query = queries[idx]
                query_num = idx + 1
                
                # Calculate progress and ETA
                elapsed = (datetime.now() - start_time).total_seconds()
                if query_num > start_query + 1:
                    avg_time_per_query = elapsed / (query_num - start_query - 1)
                    remaining_queries = total_queries - query_num
                    eta_seconds = avg_time_per_query * remaining_queries
                    eta_minutes = int(eta_seconds / 60)
                    
                    print(f"\n[{query_num}/{total_queries}] {query}")
                    print(f"  ⏱ ETA: ~{eta_minutes} minutes remaining (avg {avg_time_per_query:.1f}s/query)")
                else:
                    print(f"\n[{query_num}/{total_queries}] {query}")
                
                # Process platforms IN PARALLEL using ThreadPoolExecutor
                print(f"  🚀 Starting parallel execution with {len(self.clients)} workers...")
                start_parallel = time.time()
                
                platform_futures = {}
                with ThreadPoolExecutor(max_workers=len(self.clients)) as executor:
                    # Submit all platforms at once
                    for platform_name in self.clients.keys():
                        future = executor.submit(
                            self.process_query_on_platform, 
                            query, 
                            platform_name, 
                            runs_per_query
                        )
                        platform_futures[future] = platform_name
                    
                    # Collect results as they complete
                    for future in as_completed(platform_futures):
                        platform_name = platform_futures[future]
                        try:
                            result = future.result()
                            
                            # Append to correct position
                            if len(platform_results[platform_name]) < query_num:
                                platform_results[platform_name].append(result)
                            else:
                                platform_results[platform_name][idx] = result
                        except Exception as e:
                            print(f"\n    ✗ {platform_name} failed: {e}")
                            # Add empty result for failed platform
                            empty_result = {
                                'query': query,
                                'query_brands': [],
                                'organic_competitors': [],
                                'all_competitors_mentioned': "",
                                'position': "",
                                'sources': [],
                                'source_recency': "Unknown",
                                'models': [],
                                'key_messages': {},
                                'tone': "N",
                                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                'total_runs': 0,
                                'platform': platform_name
                            }
                            if len(platform_results[platform_name]) < query_num:
                                platform_results[platform_name].append(empty_result)
                            else:
                                platform_results[platform_name][idx] = empty_result
                
                parallel_time = time.time() - start_parallel
                print(f"  ✅ Parallel execution completed in: {parallel_time:.1f}s")
                
                # Check if parallel is actually working
                if parallel_time > 300:  # More than 5 minutes
                    print(f"  ⚠️  WARNING: Parallel execution seems slow - might be running sequentially!")
                
                # Save checkpoint after each query
                self._save_checkpoint(checkpoint_file, platform_results, idx)
                
        except KeyboardInterrupt:
            print("\n\n⚠ Process interrupted by user")
            print(f"Progress saved. Run again to resume from query {idx + 1}")
            raise
        
        # Clean up checkpoint file on successful completion
        try:
            if os.path.exists(checkpoint_file):
                os.remove(checkpoint_file)
                print("\n✓ Checkpoint file cleaned up")
        except:
            pass
        
        total_time = (datetime.now() - start_time).total_seconds()
        
        print("\n" + "=" * 80)
        print(f"✅ COMPLETED: Processed {total_queries} queries across {len(self.clients)} platforms")
        print(f"⏱ Total time: {int(total_time / 60)} minutes {int(total_time % 60)} seconds")
        print(f"⚡ Average: {total_time / total_queries:.1f} seconds per query")
        print("=" * 80)
        
        return platform_results
