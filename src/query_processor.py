"""
Query Processor - Orchestrates query execution across platforms
"""

import time
import random
from typing import List, Dict, Any
from src.api_clients import LLMClientFactory
from src.analyzer import BrandAnalyzer
from src.config_manager import ConfigManager


class QueryProcessor:
    """Processes queries across multiple LLM platforms"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.analyzer = BrandAnalyzer(config_manager)
        self.clients = self._initialize_clients()
        self.system_prompt = config_manager.get_system_prompt()
    
    def _initialize_clients(self):
        """Initialize LLM clients for enabled platforms"""
        clients = []
        enabled_platforms = self.config.get_enabled_platforms()
        
        for platform in enabled_platforms:
            try:
                client = LLMClientFactory.create_client(platform)
                clients.append(client)
                print(f"✓ {client.get_platform_name()} initialized")
            except Exception as e:
                print(f"✗ Failed to initialize {platform}: {e}")
        
        if not clients:
            raise ValueError("No LLM clients could be initialized")
        
        return clients
    
    def process_single_query_run(self, query: str, run_number: int, 
                                  query_brands: List[str]) -> Dict[str, Any]:
        """Process a single run of a query"""
        # Rotate through clients
        client = self.clients[run_number % len(self.clients)]
        platform = client.get_platform_name()
        
        try:
            # Add source request to query
            full_query = f"{query}\n\nIMPORTANT: List all website URLs or domain names you referenced to answer this question."
            
            # Query the platform
            response = client.query(full_query, self.system_prompt)
            
            # Analyze response
            analysis = self.analyzer.analyze_single_response(query, response, query_brands)
            analysis['platform'] = platform
            analysis['success'] = True
            
            return analysis
            
        except Exception as e:
            print(f"    ✗ Error on run {run_number + 1}: {e}")
            return {
                'brands': [],
                'sources': [],
                'models': [],
                'key_messages': {},
                'platform': platform,
                'success': False,
                'error': str(e)
            }
    
    def process_query(self, query: str, query_index: int, total_queries: int,
                     progress_callback=None) -> Dict[str, Any]:
        """Process a single query with multiple runs"""
        runs_per_query = self.config.get_runs_per_query()
        query_brands = self.analyzer.identify_query_brands(query)
        
        print(f"\n[{query_index}/{total_queries}] Processing: {query}")
        print(f"  Query mentions: {', '.join(query_brands) if query_brands else 'No specific brand'}")
        print(f"  Running {runs_per_query} times across {len(self.clients)} platforms...")
        
        results = []
        successful_runs = 0
        
        for run in range(runs_per_query):
            # Progress update
            if progress_callback:
                progress_callback(query_index, total_queries, run + 1, runs_per_query)
            
            # Process run
            result = self.process_single_query_run(query, run, query_brands)
            results.append(result)
            
            if result['success']:
                successful_runs += 1
            
            # Progress indicator
            if (run + 1) % 10 == 0:
                print(f"    Progress: {run + 1}/{runs_per_query} runs ({successful_runs} successful)")
            
            # Rate limiting - randomized sleep
            sleep_time = random.uniform(0.3, 0.8)
            time.sleep(sleep_time)
        
        print(f"  ✓ Completed: {successful_runs}/{runs_per_query} successful runs")
        
        # Aggregate results
        aggregated = self.analyzer.aggregate_results(query, results, successful_runs)
        
        return aggregated
    
    def process_all_queries(self, queries: List[str], 
                           progress_callback=None) -> List[Dict[str, Any]]:
        """Process all queries"""
        total_queries = len(queries)
        all_results = []
        
        print("\n" + "=" * 80)
        print(f"PROCESSING {total_queries} QUERIES")
        print(f"Runs per query: {self.config.get_runs_per_query()}")
        print(f"Platforms: {', '.join([c.get_platform_name() for c in self.clients])}")
        print("=" * 80)
        
        for idx, query in enumerate(queries, 1):
            result = self.process_query(query, idx, total_queries, progress_callback)
            all_results.append(result)
        
        print("\n" + "=" * 80)
        print(f"✅ COMPLETED: Processed {total_queries} queries")
        print("=" * 80)
        
        return all_results