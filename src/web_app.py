"""
Flask Web Application - Brand Monitoring Tool
"""

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, flash
from flask_cors import CORS
import os
import json
import threading
from datetime import datetime
from werkzeug.utils import secure_filename
from src.config_manager import ConfigManager
from src.query_processor import QueryProcessor
from src.report_generator import ReportGenerator

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = 'your-secret-key-change-this'  # Change this in production
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'txt'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Global state for tracking analysis progress
analysis_state = {
    'running': False,
    'current_query': 0,
    'total_queries': 0,
    'platform_status': {},
    'eta_minutes': 0,
    'logs': [],
    'error': None,
    'report_file': None
}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Home page - Configuration form"""
    # Load existing config if available
    try:
        config = ConfigManager()
        existing_config = {
            'campaign_name': config.get_campaign_name(),
            'target_brand': config.get_target_brand(),
            'competitors': ', '.join(config.get_competitors()),
            'runs_per_query': config.get_runs_per_query(),
            'platforms': config.get_enabled_platforms()
        }
    except:
        existing_config = {
            'campaign_name': 'My Campaign',
            'target_brand': '',
            'competitors': '',
            'runs_per_query': 15,
            'platforms': ['chatgpt', 'gemini', 'perplexity']
        }
    
    return render_template('index.html', config=existing_config)


@app.route('/configure', methods=['POST'])
def configure():
    """Save configuration and redirect to run page"""
    try:
        # Get form data
        campaign_name = request.form.get('campaign_name', 'Brand Campaign')
        target_brand = request.form.get('target_brand')
        competitors = request.form.get('competitors', '').split(',')
        competitors = [c.strip() for c in competitors if c.strip()]
        
        runs_per_query = int(request.form.get('runs_per_query', 15))
        
        # Get platform selections
        platforms = {
            'chatgpt': 'chatgpt' in request.form.getlist('platforms'),
            'gemini': 'gemini' in request.form.getlist('platforms'),
            'perplexity': 'perplexity' in request.form.getlist('platforms')
        }
        
        # Get queries from text area or file
        queries_text = request.form.get('queries_text', '').strip()
        queries_file = request.files.get('queries_file')
        
        queries = []
        
        if queries_text:
            # Parse queries from text area
            queries = [q.strip() for q in queries_text.split('\n') if q.strip()]
        elif queries_file and allowed_file(queries_file.filename):
            # Read queries from uploaded file
            filename = secure_filename(queries_file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            queries_file.save(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                queries = [line.strip() for line in f.readlines() if line.strip()]
        
        if not queries:
            flash('Please provide queries either in the text area or upload a file', 'error')
            return redirect(url_for('index'))
        
        if not target_brand:
            flash('Please specify a target brand', 'error')
            return redirect(url_for('index'))
        
        if not any(platforms.values()):
            flash('Please select at least one platform', 'error')
            return redirect(url_for('index'))
        
        # Create config
        config_data = {
            'campaign_name': campaign_name,
            'target_brand': target_brand,
            'competitors': competitors,
            'brand_aliases': {},
            'models': {},
            'keywords': {
                'comfort': ['comfortable', 'comfort', 'cushioned', 'soft', 'padded'],
                'quality': ['quality', 'durable', 'well-made', 'long-lasting', 'sturdy'],
                'durability': ['durable', 'last', 'withstand', 'tough', 'resilient'],
                'style': ['stylish', 'fashionable', 'trendy', 'classic', 'versatile']
            },
            'queries': queries,
            'runs_per_query': runs_per_query,
            'platforms': platforms,
            'system_prompt': 'Answer as a UK consumer searching online. Keep answers factual and neutral.'
        }
        
        # Save config
        with open('config/config.json', 'w') as f:
            json.dump(config_data, f, indent=2)
        
        flash(f'Configuration saved! Ready to analyze {len(queries)} queries', 'success')
        return redirect(url_for('run'))
        
    except Exception as e:
        flash(f'Error saving configuration: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/run')
def run():
    """Run analysis page"""
    return render_template('run.html')


@app.route('/start_analysis', methods=['POST'])
def start_analysis():
    """Start the analysis in a background thread"""
    global analysis_state
    
    if analysis_state['running']:
        return jsonify({'error': 'Analysis already running'}), 400
    
    # Reset state
    analysis_state = {
        'running': True,
        'current_query': 0,
        'total_queries': 0,
        'platform_status': {},
        'eta_minutes': 0,
        'logs': [],
        'error': None,
        'report_file': None
    }
    
    # Start analysis in background thread
    thread = threading.Thread(target=run_analysis_background)
    thread.daemon = True
    thread.start()
    
    return jsonify({'status': 'started'})


def run_analysis_background():
    """Run the analysis in background"""
    global analysis_state
    
    try:
        # Load config
        config = ConfigManager()
        queries = config.get_queries()
        
        analysis_state['total_queries'] = len(queries)
        analysis_state['logs'].append(f"Starting analysis of {len(queries)} queries...")
        
        # Initialize processor
        processor = QueryProcessor(config)
        
        # Run queries
        platform_results = processor.process_all_queries(queries)
        
        # Generate report
        analysis_state['logs'].append("Generating Excel report...")
        report_gen = ReportGenerator(config)
        report_file = report_gen.create_report(platform_results)
        
        analysis_state['report_file'] = report_file
        analysis_state['logs'].append(f"✅ Complete! Report: {report_file}")
        analysis_state['running'] = False
        
    except Exception as e:
        analysis_state['error'] = str(e)
        analysis_state['logs'].append(f"❌ Error: {str(e)}")
        analysis_state['running'] = False


@app.route('/status')
def status():
    """Get current analysis status"""
    return jsonify(analysis_state)


@app.route('/results')
def results():
    """View past results"""
    # List all Excel files in output folder
    reports = []
    if os.path.exists(OUTPUT_FOLDER):
        for filename in os.listdir(OUTPUT_FOLDER):
            if filename.endswith('.xlsx'):
                filepath = os.path.join(OUTPUT_FOLDER, filename)
                file_stat = os.stat(filepath)
                reports.append({
                    'filename': filename,
                    'size': f"{file_stat.st_size / 1024:.1f} KB",
                    'created': datetime.fromtimestamp(file_stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
                })
    
    # Sort by creation time (newest first)
    reports.sort(key=lambda x: x['created'], reverse=True)
    
    return render_template('results.html', reports=reports)


@app.route('/download/<filename>')
def download(filename):
    """Download a report file"""
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        flash('File not found', 'error')
        return redirect(url_for('results'))


@app.route('/delete/<filename>', methods=['POST'])
def delete_report(filename):
    """Delete a report file"""
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        flash(f'Deleted {filename}', 'success')
    else:
        flash('File not found', 'error')
    return redirect(url_for('results'))


if __name__ == '__main__':
    print("\n" + "="*60)
    print("  BRAND MONITORING TOOL - Web Interface")
    print("="*60)
    print("\n  🌐 Starting web server...")
    print("  📍 Open your browser to: http://localhost:5000")
    print("\n" + "="*60 + "\n")
    
    app.run(debug=True, port=5000, host='0.0.0.0')