# Brand Monitoring Tool - Multi-Platform LLM Analysis

A powerful Python-based tool for analyzing brand mentions and competitive intelligence across multiple Large Language Model (LLM) platforms including ChatGPT, Gemini, and Perplexity.

## 🎯 Overview

This tool helps marketing and brand teams understand how their brand and competitors are being mentioned by AI assistants. By running queries multiple times across different LLM platforms, it provides statistical insights into:

- Brand mention frequency and positioning
- Competitive landscape analysis
- Source attribution and citation patterns
- Product/model mentions
- Key message effectiveness
- Sentiment and tone analysis

## ✨ Features

### Core Functionality
- **Multi-Platform Integration**: Query ChatGPT, Gemini, and Perplexity simultaneously
- **Scalable Analysis**: Run each query 100+ times for statistical reliability
- **Smart Brand Detection**: Handles brand variations and aliases (e.g., "Dr Martens", "Dr. Martens", "DMs", "Docs")
- **Competitive Intelligence**: Separates brands mentioned in queries from organic competitor mentions
- **Source Tracking**: Identifies and counts website citations across responses
- **Model/Style Extraction**: Detects specific product models mentioned
- **Key Message Analysis**: Tracks custom keyword categories across responses

### Configuration
- **No-Code Setup**: JSON-based configuration, no programming required
- **Flexible Queries**: Support for 25-50+ user queries per campaign
- **Custom Keywords**: Define positive, negative, and category-specific keywords
- **Brand Aliases**: Configure variations and abbreviations for accurate detection
- **Rate Limiting**: Built-in randomized delays to respect API limits

### Reporting
- **Professional Excel Output**: Formatted reports with headers and styling
- **Timestamped Results**: Automatic file naming with date/time stamps
- **Aggregated Statistics**: Percentage-based likelihood scores
- **Comprehensive Data**: Sources, models, key messages all in one report

## 📋 Requirements

- Python 3.8+
- OpenAI API key (for ChatGPT)
- Google Gemini API key
- Perplexity API key
- Internet connection

## 🚀 Installation

### 1. Clone or Download the Project
```bash
git clone <your-repo-url>
cd brand-monitoring-tool
```

### 2. Create Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up API Keys

Create a `.env` file in the project root:
```bash
OPENAI_API_KEY=your_openai_key_here
GEMINI_API_KEY=your_gemini_key_here
PERPLEXITY_API_KEY=your_perplexity_key_here
```


## ⚙️ Configuration

### 1. Edit Campaign Settings

Edit `config/config.json`:
```json
{
  "campaign_name": "Your Brand Campaign Name",
  "target_brand": "Your Brand",
  "competitors": [
    "Competitor 1",
    "Competitor 2",
    "Competitor 3"
  ],
  "brand_aliases": {
    "Your Brand": ["your brand", "yourbrand", "YB"]
  },
  "keywords": {
    "comfort": ["comfortable", "comfort", "cushioned"],
    "quality": ["quality", "durable", "well-made"],
    "value": ["affordable", "value", "worth"]
  },
  "runs_per_query": 100, #this is the number of times each query will be run
  "platforms": {
    "chatgpt": true,
    "gemini": true,
    "perplexity": true
  }
}
```

### 2. Add Your Queries

Create `client_queries.txt` with one query per line:
```text
Is [Your Brand] comfortable?
What are the best brands for [category]?
Which [product type] should I buy?
How does [Your Brand] compare to competitors?
```

**Pro tip**: Mix brand-specific queries with general category queries for comprehensive analysis.

## 🎮 Usage

### Basic Usage
```bash
python -m src.main
```

### What Happens:
1. Loads configuration from `config/config.json`
2. Loads queries from `client_queries.txt`
3. Initializes connections to enabled LLM platforms
4. Processes each query multiple times (default: 100 runs)
5. Generates Excel report in `output/` folder

### Expected Runtime

- **5 runs/query**: ~30 seconds per query
- **100 runs/query**: ~8-10 minutes per query
- **37 queries × 100 runs**: ~5-6 hours total

The tool includes rate limiting to respect API quotas.

## 📊 Understanding the Output

The Excel report includes these columns:

| Column | Description |
|--------|-------------|
| **Question** | The original query |
| **Query Brand (Expected)** | Brands mentioned in the question (expected to appear) |
| **Organic Competitor 1-3** | Brands NOT in query but mentioned in responses |
| **Likelihood %** | Percentage of responses that mentioned each brand |
| **Top Sources** | Most frequently cited websites/domains |
| **Models/Styles Mentioned** | Specific product models detected |
| **Key Messages** | Keyword categories detected with percentages |
| **Total Runs** | Number of successful API calls for this query |

### Interpreting Results

**High Likelihood (80-100%)**
- For query brands: Expected and healthy
- For organic competitors: Strong competitive threat

**Medium Likelihood (40-79%)**
- Indicates moderate association
- Consider investigating why

**Low Likelihood (0-39%)**
- Weak brand association
- Opportunity for improvement

## 🏗️ Project Structure
```
brand-monitoring-tool/
├── src/
│   ├── __init__.py
│   ├── api_clients.py          # LLM platform integrations
│   ├── analyzer.py              # Brand/keyword detection logic
│   ├── config_manager.py        # Configuration handling
│   ├── query_processor.py       # Query orchestration
│   ├── report_generator.py      # Excel report creation
│   └── main.py                  # Main application entry
├── config/
│   └── config.json              # Campaign configuration
├── output/                      # Generated reports (auto-created)
├── .env                         # API keys (create this)
├── client_queries.txt           # Your queries (create this)
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## 🔧 Customization

### Adding New Keywords

Edit `config/config.json`:
```json
"keywords": {
  "sustainability": ["sustainable", "eco-friendly", "green", "ethical"],
  "innovation": ["innovative", "cutting-edge", "advanced", "revolutionary"]
}
```

### Adding Brand Variations
```json
"brand_aliases": {
  "Nike": ["nike", "nikeinc", "swoosh"],
  "Adidas": ["adidas", "adi", "three stripes"]
}
```

### Adjusting Runs per Query

For testing: `"runs_per_query": 5`  
For production: `"runs_per_query": 100`

### Disabling Platforms
```json
"platforms": {
  "chatgpt": true,
  "gemini": false,    // Disable Gemini
  "perplexity": true
}
```

## 🐛 Troubleshooting

### "Configuration file not found"
- Ensure `config/config.json` exists
- Check file path is correct

### "No queries found"
- Create `client_queries.txt` in project root
- Ensure one query per line
- Check file encoding is UTF-8

### "Failed to initialize [platform]"
- Verify API key is set in `.env`
- Check API key is valid and active
- Ensure you have API credits/quota

### "Rate limit exceeded"
- Increase sleep time in `query_processor.py`
- Reduce `runs_per_query` temporarily
- Check your API usage limits

### Low Brand Detection Rates
- Add brand variations to `brand_aliases`
- Check spelling in brand names
- Review responses manually to debug

## 💡 Best Practices

1. **Start Small**: Test with 5 runs before scaling to 100+
2. **Mix Query Types**: Combine brand-specific and general category queries
3. **Update Aliases**: Regularly review and update brand variations
4. **Monitor API Costs**: Track usage across platforms
5. **Regular Analysis**: Run campaigns monthly to track trends
6. **Backup Reports**: Save historical reports for comparison


## 🔐 Security Notes

- Never commit `.env` file to version control
- Keep API keys confidential
- Rotate keys regularly
- Monitor API usage for anomalies
- Use environment variables in production

## 📝 Cost Estimation

Approximate costs per 100-run campaign (37 queries):

- ChatGPT (GPT-4): ~$15-25
- Gemini: ~$5-10
- Perplexity: ~$8-12

**Total per campaign**: ~$30-50

Costs vary based on response length and API pricing changes.


## 🙏 Acknowledgments

Built with:
- OpenAI GPT-4 API
- Google Gemini API
- Perplexity API
- Python OpenPyXL for Excel generation

---

**Version**: 1.0.0 (Stage 2 Complete)  
**Last Updated**: October 2025  
**Status**: Production Ready