import time
import re
from collections import Counter
from datetime import datetime
from src.api_clients import ChatGPTClient, GeminiClient, PerplexityClient
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

# Test queries from Izzy
QUERIES = [
    "Are Dr Martens sandals comfortable?",
    "Do Dr Martens sandals need breaking in?",
    "Are Dr Martens sandals true to size?",
    "Are Dr Martens sandals supportive for walking long distances everyday?",
    "Can you wear Dr Martens sandals everyday?",
    "How do Dr Martens sandals fit compared to Birkenstock?",
    "Are Dr Martens sandals better quality than high street brands?",
    "Which Dr Martens sandals are best for summer 2026?",
    "Why are Dr Martens sole's so chunky?",
    "How do I style Dr Martens sandals"
]

# Common footwear brands to track
BRANDS = [
    "Dr Martens", "Birkenstock", "Crocs", "Teva", "Keen", 
    "Chaco", "Reef", "Rainbow", "OluKai", "Sanuk",
    "Clarks", "Ecco", "Merrell", "Timberland", "UGG",
    "Vans", "Converse", "Nike", "Adidas", "Skechers"
]

SYSTEM_PROMPT = "Answer as a UK consumer searching online. Keep answers factual and neutral."

RUNS_PER_QUERY = 5  # Reduced for Stage 1 demo (will be 100+ in Stage 2)


def extract_brands(text: str, brand_list: list) -> list:
    """Extract mentioned brands from text"""
    found_brands = []
    text_lower = text.lower()
    
    for brand in brand_list:
        # Handle multi-word brands like "Dr Martens"
        if brand.lower() in text_lower:
            found_brands.append(brand)
    
    return found_brands


def extract_sources(text: str) -> list:
    """Extract domain names from text"""
    # Find URLs and domain patterns
    domains = re.findall(r'(?:https?://)?(?:www\.)?([A-Za-z0-9\-]+\.[A-Za-z\.]{2,})', text.lower())
    return [d for d in domains if d]


def run_demo():
    """Run Stage 1 demo across all platforms"""
    
    print("=" * 70)
    print("STAGE 1 DEMO - Multi-Platform Integration Test")
    print("=" * 70)
    print(f"Testing {len(QUERIES)} queries across 3 platforms")
    print(f"Runs per query: {RUNS_PER_QUERY}")
    print("=" * 70)
    print()
    
    # Initialize clients
    clients = [
        ChatGPTClient(),
        GeminiClient(),
        PerplexityClient()
    ]
    
    results = []
    
    for query_idx, query in enumerate(QUERIES, 1):
        print(f"[{query_idx}/{len(QUERIES)}] Processing: {query}")
        
        brands_seen = []
        sources_seen = []
        
        # Run query multiple times across platforms
        for run in range(RUNS_PER_QUERY):
            # Rotate through platforms
            client = clients[run % len(clients)]
            platform = client.get_platform_name()
            
            print(f"  Run {run+1}/{RUNS_PER_QUERY} - {platform}...", end=" ")
            
            try:
                # Add source request to query
                full_query = f"{query} Please list any websites/domains used to answer."
                
                # Query the platform
                response = client.query(full_query, SYSTEM_PROMPT)
                
                # Extract brands
                found_brands = extract_brands(response, BRANDS)
                brands_seen.extend(found_brands)
                
                # Extract sources
                found_sources = extract_sources(response)
                sources_seen.extend(found_sources)
                
                print("✓")
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                print(f"✗ Error: {e}")
        
        # Aggregate results for this query
        brand_counter = Counter(brands_seen)
        top_brands = brand_counter.most_common(3)
        
        source_counter = Counter(sources_seen)
        top_sources = source_counter.most_common(5)
        
        # Format results
        top_brand_1 = top_brands[0][0] if len(top_brands) > 0 else ""
        likelihood_1 = f"{round((top_brands[0][1]/RUNS_PER_QUERY)*100)}%" if len(top_brands) > 0 else ""
        
        top_brand_2 = top_brands[1][0] if len(top_brands) > 1 else ""
        likelihood_2 = f"{round((top_brands[1][1]/RUNS_PER_QUERY)*100)}%" if len(top_brands) > 1 else ""
        
        top_brand_3 = top_brands[2][0] if len(top_brands) > 2 else ""
        likelihood_3 = f"{round((top_brands[2][1]/RUNS_PER_QUERY)*100)}%" if len(top_brands) > 2 else ""
        
        sources_str = "; ".join([f"{d} ({c}x)" for d, c in top_sources]) if top_sources else "No sources found"
        
        results.append({
            "query": query,
            "top_brand_1": top_brand_1,
            "likelihood_1": likelihood_1,
            "top_brand_2": top_brand_2,
            "likelihood_2": likelihood_2,
            "top_brand_3": top_brand_3,
            "likelihood_3": likelihood_3,
            "sources": sources_str
        })
        
        print(f"  → Top brands: {top_brand_1} ({likelihood_1}), {top_brand_2} ({likelihood_2})")
        print()
    
    # Create Excel output
    print("=" * 70)
    print("Creating Excel report...")
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Stage 1 Demo Results"
    
    # Headers
    headers = [
        "Question",
        "Top Brand 1", "Likelihood 1",
        "Top Brand 2", "Likelihood 2",
        "Top Brand 3", "Likelihood 3",
        "Source(s) Cited"
    ]
    
    ws.append(headers)
    
    # Make headers bold
    for cell in ws[1]:
        cell.font = Font(bold=True)
    
    # Add data
    for result in results:
        ws.append([
            result["query"],
            result["top_brand_1"], result["likelihood_1"],
            result["top_brand_2"], result["likelihood_2"],
            result["top_brand_3"], result["likelihood_3"],
            result["sources"]
        ])
    
    # Format columns
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        
        for cell in col:
            cell.alignment = Alignment(wrapText=True, vertical='top')
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column].width = adjusted_width
    
    # Save file
    filename = f"stage1_demo_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    wb.save(filename)
    
    print(f"✅ Report saved: {filename}")
    print()
    print("=" * 70)
    print("STAGE 1 DEMO COMPLETE")
    print("=" * 70)
    print()
    print("NOTE: This is a Stage 1 demonstration showing all 3 platforms work.")
    print("Full features (100+ runs, advanced analytics, UI) come in Stages 2-3.")
    print()


if __name__ == "__main__":
    run_demo()