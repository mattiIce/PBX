# Call Tagging & Categorization Guide

## Overview

The Call Tagging & Categorization system provides AI-powered automatic classification of calls with custom tagging capabilities. This enables better organization, searchability, and analytics of your call data.

## Features

- **Automatic Categorization** - AI-based classification of calls
- **Custom Tags** - Create and apply custom tags
- **Rule-Based Tagging** - Define rules for automatic tagging
- **ML Classification** - Machine learning-based call categorization
- **Tag Analytics** - Insights and reporting based on tags
- **Search by Tags** - Find calls quickly using tags

## Predefined Categories

The system includes these predefined call categories:
- **Sales** - Sales-related calls
- **Support** - Customer support inquiries
- **Billing** - Billing and payment questions
- **General Inquiry** - General questions
- **Complaint** - Customer complaints
- **Emergency** - Emergency calls
- **Technical** - Technical support
- **Other** - Uncategorized calls

## Configuration

### config.yml
```yaml
features:
  call_tagging:
    enabled: true
    auto_tag: true              # Enable automatic tagging
    min_confidence: 0.7         # Minimum confidence for auto-tags (0.0-1.0)
    max_tags: 10                # Maximum tags per call
```

## Usage

### Python API

```python
from pbx.features.call_tagging import get_call_tagging, CallCategory, TagSource

tagging = get_call_tagging()

# Tag a call manually
tagging.tag_call(
    call_id='call-123',
    tags=['urgent', 'vip-customer'],
    source=TagSource.MANUAL
)

# Categorize a call
tagging.categorize_call(
    call_id='call-123',
    category=CallCategory.SUPPORT,
    confidence=0.95
)

# Get tags for a call
tags = tagging.get_call_tags('call-123')

# Search calls by tag
calls = tagging.search_by_tag('urgent')

# Get tag statistics
stats = tagging.get_tag_statistics()
```

### REST API Endpoints

#### Tag a Call
```bash
POST /api/framework/call-tagging/tag
{
  "call_id": "call-123",
  "tags": ["urgent", "vip-customer"],
  "source": "manual"
}
```

#### Categorize a Call
```bash
POST /api/framework/call-tagging/categorize
{
  "call_id": "call-123",
  "category": "support",
  "confidence": 0.95
}
```

#### Get Call Tags
```bash
GET /api/framework/call-tagging/call/{call_id}/tags
```

#### Search by Tag
```bash
GET /api/framework/call-tagging/search?tag=urgent
```

#### Get Tag Statistics
```bash
GET /api/framework/call-tagging/statistics
```

#### Create Tagging Rule
```bash
POST /api/framework/call-tagging/rule
{
  "name": "VIP Customers",
  "conditions": {
    "caller_id": ["555-0100", "555-0200"],
    "duration_min": 60
  },
  "tags": ["vip-customer"],
  "enabled": true
}
```

## Tagging Rules

### Rule Structure

Rules allow automatic tagging based on call attributes:

```python
rule = {
    'name': 'Long Support Calls',
    'conditions': {
        'category': 'support',
        'duration_min': 300,  # 5 minutes or longer
        'queue': '8001'
    },
    'tags': ['complex-issue', 'requires-follow-up'],
    'enabled': True
}

tagging.add_tagging_rule(rule)
```

### Common Rule Examples

#### Tag VIP Callers
```python
{
    'name': 'VIP Callers',
    'conditions': {
        'caller_id_prefix': ['555-01', '555-02']
    },
    'tags': ['vip-customer']
}
```

#### Tag After-Hours Calls
```python
{
    'name': 'After Hours',
    'conditions': {
        'time_range': {
            'start': '18:00',
            'end': '08:00'
        }
    },
    'tags': ['after-hours']
}
```

#### Tag Long Calls
```python
{
    'name': 'Extended Calls',
    'conditions': {
        'duration_min': 600  # 10 minutes
    },
    'tags': ['extended-call', 'review-needed']
}
```

## Auto-Tagging

The system can automatically tag calls based on:

### Content Analysis
```python
# Auto-tag based on transcription keywords
tagging.configure_keyword_detection({
    'billing': ['invoice', 'payment', 'charge', 'billing'],
    'complaint': ['dissatisfied', 'unhappy', 'problem', 'issue'],
    'sales': ['purchase', 'buy', 'product', 'pricing']
})
```

### Sentiment Analysis
```python
# Auto-tag based on sentiment
# Automatically tags calls with negative sentiment
tagging.enable_sentiment_tagging(
    negative_threshold=0.3,  # Tag if sentiment < 0.3
    positive_threshold=0.7   # Tag if sentiment > 0.7
)
```

### ML Classification
```python
# Train ML model on historical tagged calls
tagging.train_classifier(
    training_calls=['call-1', 'call-2', 'call-3'],
    features=['duration', 'queue', 'time_of_day', 'day_of_week']
)

# Auto-classify new calls
tagging.enable_ml_classification(min_confidence=0.75)
```

## Tag Analytics

### Tag Statistics
```python
stats = tagging.get_tag_statistics()
# Returns:
# {
#     'total_calls_tagged': 1523,
#     'total_tags_created': 3847,
#     'auto_tags': 2891,
#     'manual_tags': 956,
#     'top_tags': [
#         {'tag': 'support', 'count': 567},
#         {'tag': 'billing', 'count': 342},
#         {'tag': 'vip-customer', 'count': 189}
#     ]
# }
```

### Tag Distribution
```python
distribution = tagging.get_tag_distribution()
# Shows how tags are distributed across categories
```

### Tag Trends
```python
trends = tagging.get_tag_trends(
    start_date='2025-01-01',
    end_date='2025-01-31',
    interval='daily'
)
# Shows tag usage over time
```

## Admin Panel

Access Call Tagging in the admin panel:

1. Navigate to **Admin Panel** → **Framework Features** → **Call Tagging**
2. View tagged calls and statistics
3. Create and manage tagging rules
4. Configure auto-tagging settings
5. Search calls by tags
6. View tag analytics and trends

## Integration with Other Features

### Call Recording Analytics
```python
# Combine tagging with recording analysis
from pbx.features.call_recording_analytics import get_recording_analytics

analytics = get_recording_analytics()
recording_data = analytics.analyze_recording('call-123')

# Auto-tag based on analysis
if recording_data['sentiment'] < 0.3:
    tagging.tag_call('call-123', ['negative-sentiment'])
```

### Speech Analytics
```python
# Tag based on transcription analysis
from pbx.features.speech_analytics import get_speech_analytics

speech = get_speech_analytics()
transcript = speech.get_call_transcript('call-123')

# Auto-tag based on keywords in transcript
tagging.tag_from_transcript('call-123', transcript)
```

### Call Queues
```python
# Tag calls based on queue
tagging.add_tagging_rule({
    'name': 'Sales Queue',
    'conditions': {'queue': '8001'},
    'tags': ['sales-queue']
})
```

## Best Practices

### Tagging Strategy
- **Consistent Naming:** Use consistent tag names (lowercase, hyphenated)
- **Specific Tags:** Use specific tags like "billing-dispute" vs generic "billing"
- **Tag Hierarchy:** Consider hierarchical tags (e.g., "customer-vip", "customer-regular")
- **Limit Tags:** Don't over-tag; focus on meaningful categorization

### Rule Management
- **Regular Review:** Review and update rules periodically
- **Test Rules:** Test new rules with historical data first
- **Monitor Performance:** Check auto-tag accuracy regularly
- **Adjust Confidence:** Fine-tune confidence thresholds based on results

### Performance
- **Index Tags:** Ensure tag columns are indexed for fast searching
- **Batch Tagging:** Tag calls in batches for better performance
- **Cache Rules:** Cache tagging rules in memory
- **Async Processing:** Process auto-tagging asynchronously

## Database Schema

### call_tags
```sql
CREATE TABLE call_tags (
    id SERIAL PRIMARY KEY,
    call_id VARCHAR(100) NOT NULL,
    tag VARCHAR(100) NOT NULL,
    source VARCHAR(20),  -- auto, manual, rule
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_call_id (call_id),
    INDEX idx_tag (tag),
    INDEX idx_created_at (created_at)
);
```

### call_categories
```sql
CREATE TABLE call_categories (
    id SERIAL PRIMARY KEY,
    call_id VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(50) NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_category (category)
);
```

### tagging_rules
```sql
CREATE TABLE tagging_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    conditions JSONB NOT NULL,
    tags TEXT[] NOT NULL,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## Troubleshooting

### Low Auto-Tag Accuracy
**Solution:**
- Reduce min_confidence threshold
- Review and improve tagging rules
- Retrain ML classifier with more data
- Add more keyword definitions

### Too Many Tags per Call
**Solution:**
- Increase min_confidence threshold
- Reduce max_tags_per_call limit
- Review and consolidate similar tags
- Disable overlapping tagging rules

### Search Performance Issues
**Solution:**
- Ensure indexes are created on tag columns
- Use tag IDs instead of tag names for searches
- Implement tag caching
- Archive old tagged calls

## Next Steps

1. **Define Tag Strategy:** Plan your tagging taxonomy
2. **Configure Rules:** Set up initial tagging rules
3. **Enable Auto-Tagging:** Turn on automatic tagging
4. **Monitor Accuracy:** Review auto-tag results
5. **Tune Settings:** Adjust confidence thresholds
6. **Build Reports:** Create tag-based analytics

## See Also

- [FRAMEWORK_IMPLEMENTATION_GUIDE.md](FRAMEWORK_IMPLEMENTATION_GUIDE.md)
- [CALL_RECORDING_ANALYTICS_GUIDE.md](CALL_RECORDING_ANALYTICS_GUIDE.md)
- [SPEECH_ANALYTICS_GUIDE.md](SPEECH_ANALYTICS_GUIDE.md)
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
