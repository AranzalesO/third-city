"""
Report Generator - Creates Excel reports from analysis results
"""

import os
from datetime import datetime
from typing import List, Dict, Any
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from src.config_manager import ConfigManager


class ReportGenerator:
    """Generates Excel reports from analysis results"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.campaign_name = config_manager.get_campaign_name()
        self.target_brand = config_manager.get_target_brand()
    
    def create_report(self, results: List[Dict[str, Any]], 
                     output_dir: str = "output") -> str:
        """Create Excel report from results"""
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Brand Analysis"
        
        # Add headers
        headers = [
            "Question",
            "Query Brand (Expected)",
            "Organic Competitor 1", "Likelihood 1",
            "Organic Competitor 2", "Likelihood 2",
            "Organic Competitor 3", "Likelihood 3",
            "Top Sources",
            "Models/Styles Mentioned",
            "Key Messages",
            "Total Runs"
        ]
        
        ws.append(headers)
        
        # Style headers
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        
        # Add data rows
        for result in results:
            row_data = self._format_result_row(result)
            ws.append(row_data)
        
        # Format columns
        self._format_columns(ws)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        filename = f"{output_dir}/{self.campaign_name.replace(' ', '_')}_{timestamp}.xlsx"
        
        # Save workbook
        wb.save(filename)
        
        return filename
    
    def _format_result_row(self, result: Dict[str, Any]) -> List[Any]:
        """Format a single result into a row"""
        query = result['query']
        
        # Query brands
        query_brands = result['query_brands']
        if query_brands:
            query_brand_str = ", ".join([f"{brand} ({likelihood}%)" 
                                         for brand, likelihood in query_brands])
        else:
            query_brand_str = "None"
        
        # Organic competitors
        organic = result['organic_competitors']
        
        organic_1 = organic[0][0] if len(organic) > 0 else ""
        organic_1_pct = f"{round((organic[0][1]/result['total_runs'])*100)}%" if len(organic) > 0 else ""
        
        organic_2 = organic[1][0] if len(organic) > 1 else ""
        organic_2_pct = f"{round((organic[1][1]/result['total_runs'])*100)}%" if len(organic) > 1 else ""
        
        organic_3 = organic[2][0] if len(organic) > 2 else ""
        organic_3_pct = f"{round((organic[2][1]/result['total_runs'])*100)}%" if len(organic) > 2 else ""
        
        # Sources
        sources = result['sources']
        sources_str = "; ".join([f"{domain} ({count}x)" for domain, count in sources[:5]]) \
                     if sources else "No sources found"
        
        # Models
        models = result['models']
        models_str = "; ".join([f"{model} ({count}x)" for model, count in models[:5]]) \
                    if models else "None detected"
        
        # Key messages
        key_messages = result['key_messages']
        total_runs = result['total_runs']
        key_msg_list = [f"{cat.title()}: {round((count/total_runs)*100)}%" 
                       for cat, count in key_messages.items() if count > 0]
        key_msg_str = ", ".join(key_msg_list) if key_msg_list else "No key messages detected"
        
        return [
            query,
            query_brand_str,
            organic_1, organic_1_pct,
            organic_2, organic_2_pct,
            organic_3, organic_3_pct,
            sources_str,
            models_str,
            key_msg_str,
            total_runs
        ]
    
    def _format_columns(self, ws):
        """Format column widths and cell alignment"""
        # Column widths
        column_widths = {
            'A': 50,  # Question
            'B': 25,  # Query Brand
            'C': 20,  # Organic 1
            'D': 12,  # Likelihood 1
            'E': 20,  # Organic 2
            'F': 12,  # Likelihood 2
            'G': 20,  # Organic 3
            'H': 12,  # Likelihood 3
            'I': 50,  # Sources
            'J': 40,  # Models
            'K': 50,  # Key Messages
            'L': 12,  # Total Runs
        }
        
        for col, width in column_widths.items():
            ws.column_dimensions[col].width = width
        
        # Cell alignment
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(vertical='top', wrap_text=True)