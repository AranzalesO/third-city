# src/web_app.py
"""
Flask Web Application - Brand Monitoring Tool
"""

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, flash
from flask_cors import CORS
import os
import json
import sys
import threading
from datetime import datetime
from werkzeug.utils import secure_filename

# Setup paths
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SRC_DIR)
sys.path.insert(0, SRC_DIR)

# Import our modules (without src. prefix since we added SRC_DIR to path)
from config_manager import ConfigManager
from query_processor import QueryProcessor
from report_generator import ReportGenerator
import secrets

app = Flask(__name__, 
            template_folder=os.path.join(PROJECT_ROOT, 'templates'),
            static_folder=os.path.join(PROJECT_ROOT, 'static'))
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
CORS(app)

# Configuration - Use absolute paths
UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, 'uploads')
OUTPUT_FOLDER = os.path.join(PROJECT_ROOT, 'output')
CONFIG_FOLDER = os.path.join(PROJECT_ROOT, 'config')
ALLOWED_EXTENSIONS = {'txt'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(CONFIG_FOLDER, exist_ok=True)

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
        target_brand = request.form.get('target_brand', '').strip()
        competitors = request.form.get('competitors', '').split(',')
        competitors = [c.strip() for c in competitors if c.strip()]
        
        # IMPORTANT: Remove target brand from competitors if present
        target_brand_lower = target_brand.lower()
        competitors = [c for c in competitors if c.lower() != target_brand_lower]
        
        # Get models
        models_input = request.form.get('models', '').split(',')
        models = [m.strip() for m in models_input if m.strip()]
        
        # Get keywords with custom category names
        keywords = {}
        
        cat1_name = request.form.get('category_name_1', 'Comfort').strip() or 'Comfort'
        cat1_kw = [k.strip() for k in request.form.get('keywords_1', '').split(',') if k.strip()]
        if cat1_kw:
            keywords[cat1_name] = cat1_kw
        
        cat2_name = request.form.get('category_name_2', 'Quality').strip() or 'Quality'
        cat2_kw = [k.strip() for k in request.form.get('keywords_2', '').split(',') if k.strip()]
        if cat2_kw:
            keywords[cat2_name] = cat2_kw
        
        cat3_name = request.form.get('category_name_3', 'Durability').strip() or 'Durability'
        cat3_kw = [k.strip() for k in request.form.get('keywords_3', '').split(',') if k.strip()]
        if cat3_kw:
            keywords[cat3_name] = cat3_kw
        
        cat4_name = request.form.get('category_name_4', 'Style').strip() or 'Style'
        cat4_kw = [k.strip() for k in request.form.get('keywords_4', '').split(',') if k.strip()]
        if cat4_kw:
            keywords[cat4_name] = cat4_kw
        
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
            queries = [q.strip() for q in queries_text.split('\n') if q.strip()]
        elif queries_file and allowed_file(queries_file.filename):
            filename = secure_filename(queries_file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            queries_file.save(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                queries = [line.strip() for line in f.readlines() if line.strip()]
        
        # Validation
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
            'models': models,
            'keywords': keywords,  # Now with custom category names
            'queries': queries,
            'runs_per_query': runs_per_query,
            'platforms': platforms,
            'system_prompt': 'Answer as a UK consumer searching online. Keep answers factual and neutral.'
        }
        
        # Save config to correct location
        config_file = os.path.join(CONFIG_FOLDER, 'config.json')
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        flash(f'Configuration saved! Ready to analyze {len(queries)} queries across {sum(platforms.values())} platforms', 'success')
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
    
    thread = threading.Thread(target=run_analysis_background)
    thread.daemon = True
    thread.start()
    
    return jsonify({'status': 'started'})


def run_analysis_background():
    """Run the analysis in background"""
    global analysis_state

    try:
        # Clear any existing checkpoint to ensure fresh analysis
        checkpoint_file = os.path.join(OUTPUT_FOLDER, 'checkpoint.json')
        if os.path.exists(checkpoint_file):
            os.remove(checkpoint_file)
            analysis_state['logs'].append("Cleared old checkpoint - starting fresh analysis")

        # Force reload config from file (don't use cached instance)
        config_file = os.path.join(CONFIG_FOLDER, 'config.json')
        config = ConfigManager(config_file)
        queries = config.get_queries()

        analysis_state['total_queries'] = len(queries)
        analysis_state['logs'].append(f"Starting analysis of {len(queries)} queries...")

        # Log each query for debugging
        for i, q in enumerate(queries, 1):
            analysis_state['logs'].append(f"  Query {i}: {q}")

        processor = QueryProcessor(config)
        platform_results = processor.process_all_queries(queries)

        # Log summary of results to verify fresh data
        total_results = sum(len(results) for results in platform_results.values())
        analysis_state['logs'].append(f"Processed {total_results} total results across {len(platform_results)} platforms")

        analysis_state['logs'].append("Generating Excel report...")
        report_gen = ReportGenerator(config)
        report_file = report_gen.create_report(platform_results, OUTPUT_FOLDER)

        # Verify the file was actually created
        if os.path.exists(report_file):
            file_size = os.path.getsize(report_file) / 1024  # KB
            analysis_state['logs'].append(f"Report created: {os.path.basename(report_file)} ({file_size:.1f} KB)")
        else:
            analysis_state['logs'].append(f"⚠️ Warning: Report file not found at {report_file}")

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
    
    reports.sort(key=lambda x: x['created'], reverse=True)
    
    return render_template('results.html', reports=reports)


@app.route('/download/<filename>')
def download(filename):
    """Download a report file"""
    filepath = os.path.join(OUTPUT_FOLDER, secure_filename(filename))
    
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=filename)
    else:
        flash('File not found', 'error')
        return redirect(url_for('results'))


@app.route('/delete/<filename>', methods=['POST'])
def delete_report(filename):
    """Delete a report file"""
    filepath = os.path.join(OUTPUT_FOLDER, secure_filename(filename))
    
    if os.path.exists(filepath):
        os.remove(filepath)
        flash(f'Deleted {filename}', 'success')
    else:
        flash('File not found', 'error')
    return redirect(url_for('results'))


if __name__ == '__main__':
    # Check if running in production
    is_production = os.environ.get('RENDER') or os.environ.get('PORT')
    
    if is_production:
        # Production mode
        port = int(os.environ.get('PORT', 5000))
        print(f"Starting production server on port {port}...")
        app.run(debug=False, port=port, host='0.0.0.0')
    else:
        # Development mode
        print("\n" + "="*60)
        print("  BRAND MONITORING TOOL - Web Interface")
        print("="*60)
        print("\n  🌐 Starting web server...")
        print(f"  📁 Project root: {PROJECT_ROOT}")
        print(f"  📁 Output folder: {OUTPUT_FOLDER}")
        print("  📍 Open your browser to: http://localhost:5000")
        print("\n" + "="*60 + "\n")
        
        app.run(debug=True, port=5000, host='0.0.0.0')