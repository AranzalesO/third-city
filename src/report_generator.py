# src/report_generator.py - CORRECTED VERSION
"""
Report Generator - Creates Excel reports matching client template exactly
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
    
    def create_report(self, platform_results: Dict[str, List[Dict[str, Any]]], 
                     output_dir: str = "output") -> str:
        """Create Excel report from results - one sheet per platform"""
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Create workbook
        wb = Workbook()
        wb.remove(wb.active)  # Remove default sheet
        
        # Create sheet for each platform
        for platform_name, results in platform_results.items():
            self._create_platform_sheet(wb, platform_name, results)
        
        # Add campaign info sheet
        self._create_campaign_info_sheet(wb)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        filename = f"{output_dir}/{self.campaign_name.replace(' ', '_')}_{timestamp}.xlsx"
        
        # Save
        wb.save(filename)
        
        return filename
    
    def _create_platform_sheet(self, wb: Workbook, platform_name: str, 
                               results: List[Dict[str, Any]]):
        """Create sheet for a specific platform matching client template"""
        ws = wb.create_sheet(platform_name)
        
        # Headers - matching client template EXACTLY
        headers = [
            "Query",
            "Query brand (they want to audit)",
            "Organic competitor 1",
            "Likelihood 1",
            "Organic competitor 2",
            "Likelihood 2",
            "Organic competitor 3",
            "Likelihood 3",
            "Position",
            "Competitors Mentioned",
            "Source(s) Cited",
            "Recency of primary source",
            "Inclusion of key messages - Comfort",
            "Inclusion of key messages - Quality",
            "Inclusion of key messages - Durability",
            "Inclusion of key messages - Style",
            "Tone (P/N/N)",
            "Style mentioned",
            "Time and date of query run"
        ]
        
        ws.append(headers)
        
        # Style headers
        self._style_header_row(ws, 1)
        
        # Add data rows
        for result in results:
            row_data = self._format_platform_row(result)
            ws.append(row_data)
        
        # Format columns
        self._format_columns(ws)
    
    def _format_platform_row(self, result: Dict[str, Any]) -> List[Any]:
        """Format result into row matching client template"""
        # 1. Query
        query = result['query']
        
        # 2. Query brand with percentage
        query_brands = result['query_brands']
        if query_brands:
            query_brand_str = ", ".join([f"{brand} ({likelihood}%)" 
                                         for brand, likelihood in query_brands])
        else:
            query_brand_str = ""
        
        # 3-8. Organic competitors
        organic = result['organic_competitors']
        total_runs = result['total_runs']
        
        organic_1 = organic[0][0] if len(organic) > 0 else ""
        organic_1_pct = f"{round((organic[0][1]/total_runs)*100)}%" if len(organic) > 0 else ""
        
        organic_2 = organic[1][0] if len(organic) > 1 else ""
        organic_2_pct = f"{round((organic[1][1]/total_runs)*100)}%" if len(organic) > 1 else ""
        
        organic_3 = organic[2][0] if len(organic) > 2 else ""
        organic_3_pct = f"{round((organic[2][1]/total_runs)*100)}%" if len(organic) > 2 else ""
        
        # 9. Position
        position = result.get('position', "")
        
        # 10. Competitors Mentioned (all competitors found)
        competitors_mentioned = result.get('all_competitors_mentioned', "")
        
        # 11. Sources
        sources = result['sources']
        sources_str = "; ".join([f"{domain} ({count}x)" for domain, count in sources[:5]]) \
                     if sources else ""
        
        # 12. Recency of primary source
        recency = result.get('source_recency', "")
        
        # 13-16. Key messages - as percentages
        key_messages = result['key_messages']
        comfort_pct = f"{key_messages.get('comfort', 0)}%"
        quality_pct = f"{key_messages.get('quality', 0)}%"
        durability_pct = f"{key_messages.get('durability', 0)}%"
        style_pct = f"{key_messages.get('style', 0)}%"
        
        # 17. Tone (P/N/N)
        tone = result.get('tone', "N")
        
        # 18. Style mentioned (models/sandal styles)
        models = result['models']
        models_str = ", ".join([model for model, count in models[:10]]) \
                    if models else ""
        
        # 19. Time and date of query run
        timestamp = result.get('timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        return [
            query,
            query_brand_str,
            organic_1, organic_1_pct,
            organic_2, organic_2_pct,
            organic_3, organic_3_pct,
            position,
            competitors_mentioned,
            sources_str,
            recency,
            comfort_pct,
            quality_pct,
            durability_pct,
            style_pct,
            tone,
            models_str,
            timestamp
        ]
    
    def _create_campaign_info_sheet(self, wb: Workbook):
        """Create campaign info sheet"""
        ws = wb.create_sheet("Campaign Info")
        
        info_data = [
            ["Campaign Information", ""],
            ["", ""],
            ["Campaign Name", self.config.get_campaign_name()],
            ["Target Brand", self.config.get_target_brand()],
            ["Runs per Query (per platform)", self.config.get_runs_per_query()],
            ["Date Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            ["", ""],
            ["Platforms", ""],
        ]
        
        for platform in self.config.get_enabled_platforms():
            info_data.append(["", f"✓ {platform.title()}"])
        
        info_data.append(["", ""])
        info_data.append(["Competitors", ""])
        
        for competitor in self.config.get_competitors():
            info_data.append(["", competitor])
        
        for row in info_data:
            ws.append(row)
        
        ws['A1'].font = Font(bold=True, size=14)
        ws.column_dimensions['A'].width = 30
        ws.column_dimensions['B'].width = 40
    
    def _style_header_row(self, ws, row_num: int):
        """Apply styling to header row"""
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        
        for cell in ws[row_num]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    
    def _format_columns(self, ws):
        """Format column widths"""
        column_widths = {
            'A': 50,  # Query
            'B': 25,  # Query brand
            'C': 20,  # Organic 1
            'D': 12,  # Likelihood 1
            'E': 20,  # Organic 2
            'F': 12,  # Likelihood 2
            'G': 20,  # Organic 3
            'H': 12,  # Likelihood 3
            'I': 12,  # Position
            'J': 30,  # Competitors Mentioned
            'K': 45,  # Sources
            'L': 20,  # Recency
            'M': 12,  # Comfort %
            'N': 12,  # Quality %
            'O': 12,  # Durability %
            'P': 12,  # Style %
            'Q': 8,   # Tone
            'R': 40,  # Styles mentioned
            'S': 20,  # Timestamp
        }
        
        for col, width in column_widths.items():
            ws.column_dimensions[col].width = width
        
        # Cell alignment
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(vertical='top', wrap_text=True)