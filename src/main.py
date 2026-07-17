"""
Main Application - Brand Monitoring Tool
"""

import sys
from datetime import datetime
from console_setup import configure_utf8_console
configure_utf8_console()

from config_manager import ConfigManager
from query_processor import QueryProcessor
from report_generator import ReportGenerator

def print_banner():
    """Print application banner"""
    print("\n" + "=" * 80)
    print("  BRAND MONITORING TOOL - Multi-Platform LLM Analysis")
    print("=" * 80)


def progress_callback(query_idx, total_queries, run_num, total_runs):
    """Callback for progress updates"""
    # This can be enhanced with more sophisticated progress tracking
    pass


def main():
    """Main application entry point"""
    print_banner()
    
    try:
        # Load configuration
        print("\n[1/4] Loading configuration...")
        config = ConfigManager()
        print(f"✓ Campaign: {config.get_campaign_name()}")
        print(f"✓ Target Brand: {config.get_target_brand()}")
        print(f"✓ Competitors: {len(config.get_competitors())}")
        print(f"✓ Runs per query: {config.get_runs_per_query()}")
        
        # Load queries
        print("\n[2/4] Loading queries...")
        queries = config.get_queries()
        
        if not queries:
            # Try to load from file
            query_file = "client_queries.txt"
            try:
                queries = config.load_queries_from_file(query_file)
                print(f"✓ Loaded {len(queries)} queries from {query_file}")
            except FileNotFoundError:
                print(f"✗ No queries found in config and {query_file} not found")
                print("\nPlease either:")
                print("  1. Add queries to config/config.json in the 'queries' array")
                print("  2. Create a client_queries.txt file with one query per line")
                sys.exit(1)
        else:
            print(f"✓ Loaded {len(queries)} queries from config")
        
        if len(queries) == 0:
            print("✗ No queries to process")
            sys.exit(1)
        
        # Initialize processor
        print("\n[3/4] Initializing LLM clients...")
        processor = QueryProcessor(config)
        
        # Process queries
        print("\n[4/4] Processing queries...")
        start_time = datetime.now()
        
        results = processor.process_all_queries(queries, progress_callback)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Generate report
        print("\n[5/5] Generating Excel report...")
        report_gen = ReportGenerator(config)
        filename = report_gen.create_report(results)
        
        # Summary
        print("\n" + "=" * 80)
        print("  ANALYSIS COMPLETE")
        print("=" * 80)
        print(f"Total queries processed: {len(results)}")
        print(f"Total time: {int(duration // 60)}m {int(duration % 60)}s")
        print(f"Report saved: {filename}")
        print("=" * 80)
        print()
        
    except KeyboardInterrupt:
        print("\n\n✗ Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()