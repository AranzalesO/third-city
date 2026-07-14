# src/web_app.py
"""
Flask Web Application - Brand Monitoring Tool
"""

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, flash, session
from flask_cors import CORS
import os
import json
import sys
import threading
import time
from datetime import datetime
from werkzeug.utils import secure_filename

# Windows consoles default to a legacy codepage (e.g. cp1252) that can't
# encode the checkmark/emoji characters used in status prints below, which
# crashes the whole analysis with UnicodeEncodeError before any query runs.
# Force UTF-8 on stdout/stderr so logging never takes down the pipeline.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        _stream.reconfigure(encoding='utf-8', errors='replace')

# Setup paths
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SRC_DIR)
sys.path.insert(0, SRC_DIR)

# Import our modules (without src. prefix since we added SRC_DIR to path)
from config_manager import ConfigManager
from query_processor import QueryProcessor
from report_generator import ReportGenerator
from translations import TRANSLATIONS, DEFAULT_LANG, get_translator
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


def get_locale():
    """Get the current user's language, defaulting to Spanish."""
    return session.get('lang', DEFAULT_LANG)


@app.context_processor
def inject_i18n():
    lang = get_locale()
    return {
        't': get_translator(lang),
        'lang': lang,
        'translations_json': TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANG])
    }


@app.route('/set_language/<lang_code>')
def set_language(lang_code):
    """Switch the UI language between Spanish and English"""
    if lang_code in TRANSLATIONS:
        session['lang'] = lang_code
    return redirect(request.referrer or url_for('index'))

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
        # Always load from explicit path to avoid caching issues
        config_file = os.path.join(CONFIG_FOLDER, 'config.json')
        config = ConfigManager(config_file)
        existing_config = {
            'campaign_name': config.get_campaign_name(),
            'target_brand': config.get_target_brand(),
            'competitors': ', '.join(config.get_competitors()),
            'runs_per_query': config.get_runs_per_query(),
            'platforms': config.get_enabled_platforms()
        }
    except:
        existing_config = {
            'campaign_name': get_translator(get_locale())('default_campaign_name'),
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
        
        t = get_translator(get_locale())

        # Validation
        if not queries:
            flash(t('flash_missing_queries'), 'error')
            return redirect(url_for('index'))

        if not target_brand:
            flash(t('flash_missing_brand'), 'error')
            return redirect(url_for('index'))

        if not any(platforms.values()):
            flash(t('flash_missing_platform'), 'error')
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
        
        # Save config to correct location with explicit flushing
        config_file = os.path.join(CONFIG_FOLDER, 'config.json')
        print(f"[CONFIG SAVE] ========================================")
        print(f"[CONFIG SAVE] Saving config to: {config_file}")
        print(f"[CONFIG SAVE] Campaign name: '{campaign_name}'")
        print(f"[CONFIG SAVE] Target brand: '{target_brand}'")
        print(f"[CONFIG SAVE] Queries ({len(queries)} total): {queries[:3]}...")  # Show first 3
        print(f"[CONFIG SAVE] Platforms: {platforms}")

        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
            f.flush()  # Force write to disk
            os.fsync(f.fileno())  # Ensure OS writes to disk

        print(f"[CONFIG SAVE] File written and flushed to disk")

        # CRITICAL: Longer delay for Render's networked filesystem to sync
        # Render uses networked storage which can have propagation delays
        print(f"[CONFIG SAVE] Waiting 2 seconds for filesystem sync...")
        time.sleep(2.0)  # Increased from 0.5s to 2.0s for Render

        # Verify the file was actually written correctly
        print(f"[CONFIG VERIFY] Reading back from disk to verify...")
        with open(config_file, 'r') as f:
            verify_config = json.load(f)
            verified_name = verify_config.get('campaign_name')
            verified_brand = verify_config.get('target_brand')
            verified_queries = verify_config.get('queries', [])

            print(f"[CONFIG VERIFY] Read back campaign_name: '{verified_name}'")
            print(f"[CONFIG VERIFY] Read back target_brand: '{verified_brand}'")
            print(f"[CONFIG VERIFY] Read back queries count: {len(verified_queries)}")

            # Check campaign name
            if verified_name != campaign_name:
                error_msg = f'Config verification failed! Expected campaign_name="{campaign_name}" but got "{verified_name}"'
                print(f"[CONFIG ERROR] {error_msg}")
                flash(f'Warning: {error_msg}', 'error')
                return redirect(url_for('index'))

            # Check target brand
            if verified_brand != target_brand:
                error_msg = f'Config verification failed! Expected target_brand="{target_brand}" but got "{verified_brand}"'
                print(f"[CONFIG ERROR] {error_msg}")
                flash(f'Warning: {error_msg}', 'error')
                return redirect(url_for('index'))

            # Check queries
            if len(verified_queries) != len(queries):
                error_msg = f'Config verification failed! Expected {len(queries)} queries but got {len(verified_queries)}'
                print(f"[CONFIG ERROR] {error_msg}")
                flash(f'Warning: {error_msg}', 'error')
                return redirect(url_for('index'))

            print(f"[CONFIG SUCCESS] ✅ All verification checks passed!")
            print(f"[CONFIG SUCCESS] Campaign: '{verified_name}' | Brand: '{verified_brand}' | Queries: {len(verified_queries)}")
            print(f"[CONFIG SAVE] ========================================")

        success_msg = t('flash_config_saved', n=len(queries), p=sum(platforms.values()))
        print(f"[CONFIG SAVE] {success_msg}")
        flash(success_msg, 'success')
        return redirect(url_for('run'))

    except Exception as e:
        flash(get_translator(get_locale())('flash_error_saving', e=str(e)), 'error')
        return redirect(url_for('index'))
    

@app.route('/run')
def run():
    """Run analysis page"""
    global analysis_state

    # CRITICAL FIX: Clear report_file when user navigates to /run page
    # This prevents showing old reports from previous analyses
    if not analysis_state.get('running', False):
        # If not currently running, clear any old report file
        if analysis_state.get('report_file'):
            print(f"[RUN PAGE] Clearing old report file: {analysis_state.get('report_file')}")
            analysis_state['report_file'] = None
            analysis_state['logs'] = []
            analysis_state['error'] = None

    # Show current config to help debug issues
    current_config = {}
    try:
        config_file = os.path.join(CONFIG_FOLDER, 'config.json')
        with open(config_file, 'r') as f:
            raw_config = json.load(f)
            current_config = {
                'campaign_name': raw_config.get('campaign_name', 'N/A'),
                'target_brand': raw_config.get('target_brand', 'N/A'),
                'query_count': len(raw_config.get('queries', []))
            }
    except Exception as e:
        current_config = {'error': str(e)}

    # Check for stale running state
    if analysis_state.get('running'):
        current_time = time.time()
        last_update = analysis_state.get('last_update', 0)

        # If last update was more than 6 hours ago, reset state (handles very long campaigns)
        if current_time - last_update > 2160000:  # 6 hours (was 10 min, too aggressive)
            print(f"[RUN PAGE] Resetting stale running state (last update {int((current_time - last_update)/60)} min ago)")
            analysis_state = {
                'running': False,
                'current_query': 0,
                'total_queries': 0,
                'platform_status': {},
                'eta_minutes': 0,
                'logs': [],
                'error': None,
                'report_file': None,
                'last_update': time.time()
            }

    return render_template('run.html', current_config=current_config)


@app.route('/start_analysis', methods=['POST'])
def start_analysis():
    """Start the analysis in a background thread"""
    global analysis_state

    # CRITICAL: Prevent multiple analyses from running simultaneously
    # This prevents config from being changed mid-analysis
    if analysis_state.get('running', False):
        current_time = time.time()
        last_update = analysis_state.get('last_update', 0)

        # Only allow reset if truly stale (6 hours for very long campaigns)
        if current_time - last_update > 21600:  # 6 hours (was 10 min, too aggressive)
            analysis_state['logs'].append("⚠️ Detected stale state (6+ hours), forcing reset...")
        else:
            # Analysis is actively running - reject the request
            time_running = int(current_time - last_update)
            return jsonify({
                'error': f'Analysis already running (active {time_running}s ago). Please wait for it to complete.'
            }), 400

    # CRITICAL: Clear old report_file reference from state (but keep actual files)
    old_report = analysis_state.get('report_file')
    if old_report:
        print(f"[START ANALYSIS] Clearing old report reference: {old_report}")
        print(f"[START ANALYSIS] Note: Old reports preserved in output/ folder - use Results page to manage")

    # Always reset state completely for fresh start
    analysis_state = {
        'running': True,
        'current_query': 0,
        'total_queries': 0,
        'platform_status': {},
        'eta_minutes': 0,
        'logs': [],
        'error': None,
        'report_file': None,  # CRITICAL: Ensure this is None for fresh start
        'last_update': time.time()
    }

    print(f"[START ANALYSIS] State reset complete - report_file is now: {analysis_state.get('report_file')}")

    thread = threading.Thread(target=run_analysis_background)
    thread.daemon = True
    thread.start()

    return jsonify({'status': 'started'})


def run_analysis_background():
    """Run the analysis in background"""
    global analysis_state

    try:
        # Update timestamp at start
        analysis_state['last_update'] = time.time()

        # Clear any existing checkpoint to ensure fresh analysis
        checkpoint_file = os.path.join(OUTPUT_FOLDER, 'checkpoint.json')
        if os.path.exists(checkpoint_file):
            os.remove(checkpoint_file)
            analysis_state['logs'].append("Cleared old checkpoint - starting fresh analysis")

        # Force reload config from file (don't use cached instance)
        config_file = os.path.join(CONFIG_FOLDER, 'config.json')

        # DEBUG: Verify config file exists and check modification time
        if os.path.exists(config_file):
            file_mtime = os.path.getmtime(config_file)
            file_age_seconds = time.time() - file_mtime
            analysis_state['logs'].append(f"✓ Config file exists: {config_file}")
            analysis_state['logs'].append(f"✓ File last modified: {file_age_seconds:.1f} seconds ago")
        else:
            analysis_state['logs'].append(f"❌ ERROR: Config file not found: {config_file}")

        # DEBUG: Read raw JSON file to verify what's on disk
        analysis_state['logs'].append(f"📖 Reading config from disk...")
        with open(config_file, 'r') as f:
            raw_config = json.load(f)
            analysis_state['logs'].append(f"📖 Raw campaign_name from file: '{raw_config.get('campaign_name')}'")
            analysis_state['logs'].append(f"📖 Raw target_brand from file: '{raw_config.get('target_brand')}'")
            analysis_state['logs'].append(f"📖 Raw queries count: {len(raw_config.get('queries', []))}")

        # CRITICAL: Create config instance ONCE and reuse it throughout
        # This prevents issues if config.json is modified during analysis
        config = ConfigManager(config_file)
        analysis_state['logs'].append(f"📖 ConfigManager campaign_name: '{config.get_campaign_name()}'")
        analysis_state['logs'].append(f"📖 ConfigManager target_brand: '{config.get_target_brand()}'")

        # Store campaign name immediately to prevent it from changing
        locked_campaign_name = config.get_campaign_name()
        locked_target_brand = config.get_target_brand()
        analysis_state['logs'].append(f"🔒 LOCKED campaign_name: '{locked_campaign_name}'")
        analysis_state['logs'].append(f"🔒 LOCKED target_brand: '{locked_target_brand}'")

        queries = config.get_queries()

        analysis_state['total_queries'] = len(queries)
        analysis_state['logs'].append(f"Starting analysis of {len(queries)} queries...")
        analysis_state['last_update'] = time.time()

        # Log each query for debugging
        for i, q in enumerate(queries, 1):
            analysis_state['logs'].append(f"  Query {i}: {q}")

        analysis_state['last_update'] = time.time()
        processor = QueryProcessor(config)

        # CRITICAL: Define progress callback to update last_update during long analyses
        # This prevents 10-minute timeout from triggering on large campaigns
        logged_platform_errors = set()

        def update_progress(current_query, total_queries, eta_minutes, platform_status, platform_errors=None):
            analysis_state['current_query'] = current_query
            analysis_state['total_queries'] = total_queries
            analysis_state['eta_minutes'] = eta_minutes
            analysis_state['platform_status'] = platform_status
            analysis_state['last_update'] = time.time()  # CRITICAL: Keep state fresh

            # Surface real API errors (quota, auth, etc.) in the UI instead of only server console
            if platform_errors:
                for platform_name, errors in platform_errors.items():
                    for err in errors:
                        dedupe_key = f"{platform_name}:{err}"
                        if dedupe_key not in logged_platform_errors:
                            logged_platform_errors.add(dedupe_key)
                            analysis_state['logs'].append(f"⚠️ {platform_name} error: {err}")

        platform_results = processor.process_all_queries(queries, progress_callback=update_progress)

        # Log summary of results to verify fresh data
        total_results = sum(len(results) for results in platform_results.values())
        analysis_state['logs'].append(f"Processed {total_results} total results across {len(platform_results)} platforms")
        analysis_state['last_update'] = time.time()

        analysis_state['logs'].append("Generating Excel report...")
        # Verify our locked values haven't changed
        analysis_state['logs'].append(f"✓ Using LOCKED campaign_name: '{locked_campaign_name}'")
        analysis_state['logs'].append(f"✓ Using LOCKED target_brand: '{locked_target_brand}'")

        # Check if config file was modified during analysis (for debugging)
        with open(config_file, 'r') as f:
            current_config = json.load(f)
            current_campaign = current_config.get('campaign_name', '')
            if current_campaign != locked_campaign_name:
                analysis_state['logs'].append(f"⚠️ WARNING: Config file was modified during analysis!")
                analysis_state['logs'].append(f"   Started with: '{locked_campaign_name}'")
                analysis_state['logs'].append(f"   File now has: '{current_campaign}'")
                analysis_state['logs'].append(f"   Ignoring file changes - using original config")

        # DO NOT re-read config - use the SAME instance we created at start
        report_gen = ReportGenerator(config)
        analysis_state['logs'].append(f"DEBUG: ReportGenerator campaign_name: '{report_gen.campaign_name}'")

        report_file = report_gen.create_report(platform_results, OUTPUT_FOLDER)

        # Verify the file was actually created
        if os.path.exists(report_file):
            file_size = os.path.getsize(report_file) / 1024  # KB
            analysis_state['logs'].append(f"Report created: {os.path.basename(report_file)} ({file_size:.1f} KB)")
        else:
            analysis_state['logs'].append(f"⚠️ Warning: Report file not found at {report_file}")

        analysis_state['report_file'] = report_file
        analysis_state['logs'].append(f"✅ Complete! Report: {report_file}")
        analysis_state['last_update'] = time.time()
        analysis_state['running'] = False

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        analysis_state['error'] = str(e)
        analysis_state['logs'].append(f"❌ Error: {str(e)}")
        analysis_state['logs'].append(f"Details: {error_detail[:500]}")  # First 500 chars
        analysis_state['last_update'] = time.time()
        analysis_state['running'] = False


@app.route('/status')
def status():
    """Get current analysis status"""
    response = jsonify(analysis_state)
    # Prevent caching to ensure fresh state every time
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/reset_state', methods=['POST'])
def reset_state():
    """Manually reset analysis state - useful for clearing stuck states"""
    global analysis_state

    analysis_state = {
        'running': False,
        'current_query': 0,
        'total_queries': 0,
        'platform_status': {},
        'eta_minutes': 0,
        'logs': ['State manually reset'],
        'error': None,
        'report_file': None,
        'last_update': time.time()
    }

    return jsonify({'status': 'reset', 'message': 'Analysis state has been reset'})


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


def _safe_output_path(filename):
    """Resolve a filename to a path inside OUTPUT_FOLDER, preventing path
    traversal WITHOUT stripping Unicode characters (secure_filename mangles
    accented names like 'Vélez_...' -> 'Vlez_...', breaking downloads)."""
    # Strip any directory components to block traversal (e.g. ../../etc)
    name = os.path.basename(filename)
    filepath = os.path.normpath(os.path.join(OUTPUT_FOLDER, name))

    # Ensure the resolved path is still inside OUTPUT_FOLDER
    output_abs = os.path.abspath(OUTPUT_FOLDER)
    if os.path.commonpath([os.path.abspath(filepath), output_abs]) != output_abs:
        return None
    return filepath


@app.route('/download/<path:filename>')
def download(filename):
    """Download a report file"""
    filepath = _safe_output_path(filename)

    if filepath and os.path.exists(filepath):
        response = send_file(filepath, as_attachment=True,
                             download_name=os.path.basename(filepath))
        # CRITICAL: Prevent browser from caching Excel files
        # This ensures user always gets the latest report even if filename matches previous download
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    else:
        flash(get_translator(get_locale())('flash_file_not_found'), 'error')
        return redirect(url_for('results'))


@app.route('/delete/<path:filename>', methods=['POST'])
def delete_report(filename):
    """Delete a report file"""
    filepath = _safe_output_path(filename)
    t = get_translator(get_locale())

    if filepath and os.path.exists(filepath):
        os.remove(filepath)
        flash(t('flash_report_deleted', name=os.path.basename(filepath)), 'success')
    else:
        flash(t('flash_file_not_found'), 'error')
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