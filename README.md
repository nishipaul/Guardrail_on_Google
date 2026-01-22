# GCP Guardrail - Complete Documentation

A comprehensive content safety and guardrail system combining **Google Cloud Natural Language API** and **Model Armor** for robust text analysis, moderation, and protection.

---

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Core Concepts](#core-concepts)
4. [Available Guardrail Functions](#available-guardrail-functions)
5. [Configuration Options](#configuration-options)
6. [Categories Reference](#categories-reference)
7. [Thresholds & Severity Levels](#thresholds--severity-levels)
8. [Execution Modes](#execution-modes)
9. [Quick Start](#quick-start)
10. [Output Structure](#output-structure)

---

## Overview

GCP Guardrail provides a unified interface for content safety checks, combining two powerful Google Cloud services:

### What It Does

| Capability | Description | Use Case |
|------------|-------------|----------|
| **Sentiment Analysis** | Measures emotional tone of text | Block overly negative content |
| **Entity Detection** | Identifies people, places, organizations, PII | Prevent data leakage |
| **Text Classification** | Categorizes content into topics | Block inappropriate topics |
| **Content Moderation** | Detects harmful content categories | Filter toxic/violent content |
| **Model Armor** | Advanced AI safety checks | Prevent jailbreaks, prompt injection |

### Key Benefits

- **Dual-phase checking**: Validate both user input AND model output
- **Flexible thresholds**: Configure sensitivity per category
- **Parallel execution**: Run multiple checks simultaneously for speed
- **Automatic logging**: Track all queries and results
- **Regex fallback**: Catches PII that APIs might miss (SSN, credit cards)

---

## System Architecture

The system is organized in layers, each with a specific responsibility:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Your Application                              │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GuardrailRunner                               │
│    • Loads configuration                                         │
│    • Manages execution (sequential/parallel)                     │
│    • Applies blocking logic based on thresholds                  │
│    • Logs all queries                                            │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GeminiGuardrail                               │
│    • Unified wrapper for all guardrail types                     │
│    • Handles errors gracefully                                   │
│    • Returns standardized results                                │
└─────────────────────────────────────────────────────────────────┘
                    │                           │
                    ▼                           ▼
         ┌──────────────────┐       ┌──────────────────────────┐
         │    NLP Client    │       │   Model Armor Client     │
         │                  │       │                          │
         │  • Sentiment     │       │  • RAI Filter            │
         │  • Entities      │       │  • SDP Filter            │
         │  • Classification│       │  • Jailbreak Detection   │
         │  • Moderation    │       │  • Malicious URI Check   │
         └──────────────────┘       │  • CSAM Detection        │
                                    └──────────────────────────┘
```

### Files in the System

| File | Purpose |
|------|---------|
| `GCP_Guardrail_Runner.py` | Main interface - handles config, execution, logging |
| `Gemini_Guardrail.py` | Unified wrapper combining NLP API and Model Armor |
| `NLP_CLIENT.py` | Google Cloud Natural Language API client |
| `MODEL_ARMOR_CLIENT.py` | Google Cloud Model Armor API client |
| `ENUM_CLASSES.py` | Enums, dataclasses, and helper functions |
| `end_user.py` | Example usage script |
| `config.json` | The guardrail configuration file |
| `secrets/guardrail_secret.json` | GCP service account credentials |
| `dist/gcp_guardrail-1.0.0-py3-none-any.whl` | To install the GCP Guardrail as a package and use it directly.|

---

### Example snippet after package installation

- To install the package, Perform - pip install dist/gcp_guardrail-1.0.0-py3-none-any.whl - after downloading the complete dist folder.
- Ensure to have the secrets/service_account.json file and config.json file.
- Having other details are optional, but place on .env file if you have

Run this code -

```python
from gcp_guardrail import GuardrailRunner

runner = GuardrailRunner(
    config_path="config.json",
    key_path="path/to/service_account.json",
    project_id="your-project-id",
    location="us-central1",
    template_id="your-template-id"
)

result = runner.run("Your text here")
```

Pass user_name parameter in the GuardrailRunner() class for saving the log files with the provided user name. Default name is simpplr.

---

## Core Concepts

### Phases: Input vs Output

The system operates in two phases, each serving a different purpose:

| Phase | When It Runs | What It Checks | CheckType Used |
|-------|--------------|----------------|----------------|
| **Input** | Before sending to LLM | User's prompt/question | `USER_PROMPT` |
| **Output** | After receiving from LLM | Model's generated response | `MODEL_RESPONSE` |

**Why separate phases?**
- Input phase catches malicious user attempts (jailbreaks, prompt injection)
- Output phase ensures the model didn't generate harmful content
- Each phase can have different sensitivity thresholds

### Blocking Logic

When a check runs, the system determines if content should be "blocked" based on:

1. **Detected value** (confidence, score, salience)
2. **Configured threshold**
3. **Comparison**: If detected value meets/exceeds threshold → BLOCKED

Example: If `moderate_text` detects "Toxic" with confidence 0.75, and your threshold is 0.5, the content is blocked because 0.75 ≥ 0.5.

### Salience vs Confidence

These are different metrics used by different functions:

| Metric | Used By | Range | Meaning |
|--------|---------|-------|---------|
| **Confidence** | Moderation, Classification, Model Armor | 0.0 - 1.0 | How certain the system is about detection |
| **Salience** | Entity Detection | 0.0 - 1.0 | How important/prominent the entity is in text |
| **Score** | Sentiment Analysis | -1.0 to +1.0 | Negative to positive sentiment |
| **Magnitude** | Sentiment Analysis | 0.0 to ∞ | Intensity of emotion (regardless of direction) |

---

## Available Guardrail Functions

### 1. Sentiment Analysis (`analyze_sentiment`)

**Purpose**: Measures the emotional tone of text.

**What it returns**:
- **Score**: -1.0 (very negative) to +1.0 (very positive)
- **Magnitude**: 0.0 to infinity (emotional intensity)
- **Interpretation**: Human-readable label like "Mild Positive" or "Strong Negative"

**Score Interpretation**:

| Score Range | Interpretation |
|-------------|----------------|
| > 0.25 | Positive |
| -0.25 to 0.25 | Neutral |
| < -0.25 | Negative |

**Magnitude Interpretation**:

| Magnitude | Intensity |
|-----------|-----------|
| > 2.0 | Strong emotion |
| 1.0 - 2.0 | Moderate emotion |
| < 1.0 | Mild emotion |

**Blocking**: By default, blocks content with score ≤ -0.50 (moderately negative).

---

### 2. Entity Detection (`analyze_entities`)

**Purpose**: Identifies named entities like people, places, organizations, and PII.

**What it returns**:
- List of entities found with their type and salience
- Blocked items if entity type is in your blocked list

**How salience works**:
- 0.0 = Entity mentioned but not central to the text
- 1.0 = Entity is the main focus of the text
- Example: In "John went to Paris", both "John" and "Paris" might have salience ~0.5

**Detection Methods**:
1. **NLP API**: Detects most entity types
2. **Regex Fallback**: Catches patterns NLP API might miss (SSN, Credit Cards, Phone Numbers)

---

### 3. Text Classification (`classify_text`)

**Purpose**: Categorizes content into Google's taxonomy of topics.

**Important**: Requires minimum **20 words** to function. Shorter text returns an error.

**What it returns**:
- List of categories with confidence scores
- Categories are hierarchical paths like `/Arts & Entertainment/Music`

**Blocking**: Uses substring matching - if your blocked category "Adult" appears anywhere in the detected category path, it's blocked.

---

### 4. Content Moderation (`moderate_text`)

**Purpose**: Detects harmful content across 16 categories.

**What it returns**:
- Confidence score (0.0-1.0) for each moderation category
- Severity level derived from confidence

**Key difference from Model Armor**: NLP Moderation has a **"Violent"** category that Model Armor's RAI filter lacks.

---

### 5. Model Armor (`model_armor`)

**Purpose**: Advanced AI-specific safety checks.

**Contains 5 filters**:

| Filter | Key | What It Detects |
|--------|-----|-----------------|
| **RAI** | `rai` | Responsible AI violations (dangerous, hate speech, sexually explicit, harassment) |
| **SDP** | `sdp` | Sensitive Data Protection - PII via GCP DLP |
| **Prompt Injection** | `pi_and_jailbreak` | Attempts to manipulate the AI |
| **Malicious URIs** | `malicious_uris` | Dangerous links/URLs |
| **CSAM** | `csam` | Child safety content |

**Match States**:
- `NO_MATCH_FOUND` = Content is safe
- `MATCH_FOUND` = Content is flagged

**Important**: Model Armor is template-based - behavior depends on your GCP template configuration.

---

## Configuration Options

### Config Structure

Configuration is a JSON file with optional `input` and `output` sections:

```json
{
  "input": { ... options for checking user input ... },
  "output": { ... options for checking model output ... }
}
```

You can have:
- Only `input` phase
- Only `output` phase
- Both phases
- Different functions and thresholds per phase

### Function Names (Aliases)

These names are interchangeable in your config:

| You Can Use | Maps To |
|-------------|---------|
| `sentiment` or `analyze_sentiment` | Sentiment Analysis |
| `entities` or `analyze_entities` | Entity Detection |
| `classify` or `classify_text` | Text Classification |
| `moderate` or `moderate_text` | Content Moderation |
| `armor` or `model_armor` | Model Armor |

### Sentiment Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `analyze_sentiment_block_negative` | boolean | `true` | Enable/disable blocking |
| `analyze_sentiment_score_threshold` | float | `-0.50` | Block if score ≤ this |
| `analyze_sentiment_magnitude_threshold` | float | none | Block if magnitude ≥ this |

### Entity Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `analyze_entities_blocked_types` | list | none | Entity types to block |
| `analyze_entities_salience_threshold` | float | `0.0` | Default threshold for all types |
| `analyze_entities_salience_thresholds` | dict | none | Per-type thresholds |

### Classification Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `classify_text_blocked_categories` | list | none | Category patterns to block |
| `classify_text_threshold` | float | `0.5` | Minimum confidence to block |

### Moderation Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `moderate_text_blocked_categories` | list | all | Categories to check |
| `moderate_text_thresholds` | dict | `0.5` for all | Per-category thresholds |

---

## Categories Reference

### Moderation Categories (16 total)

| Category | Description | Common Threshold |
|----------|-------------|------------------|
| **Toxic** | General toxicity | 0.3 - 0.5 |
| **Insult** | Insulting language | 0.4 - 0.5 |
| **Profanity** | Profane/vulgar language | 0.3 - 0.5 |
| **Derogatory** | Demeaning content | 0.3 - 0.5 |
| **Sexual** | Sexual content | 0.2 - 0.4 |
| **Violent** | Violence-related content | 0.3 - 0.5 |
| **Death, Harm & Tragedy** | Content about death/harm | 0.4 - 0.6 |
| **Firearms & Weapons** | Weapons-related | 0.3 - 0.5 |
| **Illicit Drugs** | Drug-related content | 0.3 - 0.5 |
| **Public Safety** | Public safety concerns | 0.5 |
| **Health** | Health-related (informational) | 0.5 - 0.7 |
| **Religion & Belief** | Religious content | 0.5 - 0.7 |
| **War & Conflict** | War/military content | 0.5 |
| **Politics** | Political content | 0.5 - 0.7 |
| **Finance** | Financial content | 0.5 - 0.7 |
| **Legal** | Legal-related content | 0.5 - 0.7 |

**Fuzzy Name Matching**: Category names are case-insensitive and support variations:
- `"death"`, `"harm"`, `"tragedy"` all match `Death, Harm & Tragedy`
- `"firearms"`, `"weapons"` both match `Firearms & Weapons`
- `"drugs"`, `"illicit"` both match `Illicit Drugs`

### Entity Types (18 NLP API + 2 Regex-only)

**NLP API Entity Types**:

| Type | Description | Example |
|------|-------------|---------|
| `PERSON` | Person names | "John Smith" |
| `LOCATION` | Geographic locations | "New York", "France" |
| `ORGANIZATION` | Companies, agencies | "Google", "FBI" |
| `EVENT` | Events | "World Cup", "Conference" |
| `WORK_OF_ART` | Creative works | "Mona Lisa", "Star Wars" |
| `CONSUMER_GOOD` | Products | "iPhone", "Tesla Model 3" |
| `PHONE_NUMBER` | Phone numbers | "555-123-4567" |
| `ADDRESS` | Physical addresses | "123 Main St" |
| `EMAIL` | Email addresses | "user@example.com" |
| `URL` | Web URLs | "https://..." |
| `DATE` | Dates | "January 15, 2026" |
| `NUMBER` | Numeric values | "42", "3.14" |
| `PRICE` | Monetary values | "$99.99" |
| `IBAN` | Bank account numbers | International format |
| `FLIGHT_NUMBER` | Flight numbers | "AA1234" |
| `ID_NUMBER` | ID numbers | Various ID formats |

**Regex-Only Types** (not in NLP API, detected via pattern matching):

| Type | Pattern Detected |
|------|------------------|
| `SSN` | Social Security Numbers (xxx-xx-xxxx) |
| `CREDIT_CARD` | 16-digit credit card numbers |

### Model Armor RAI Categories

| Category | Description |
|----------|-------------|
| `dangerous` | Content promoting dangerous activities |
| `hate_speech` | Discriminatory or hateful content |
| `sexually_explicit` | Sexual content |
| `harassment` | Harassing or bullying content |

**Note**: Model Armor RAI does NOT have a "violent" category - use NLP Moderation for violence detection.

---

## Thresholds & Severity Levels

### Understanding Confidence

Confidence is a probability score from 0.0 to 1.0:

| Confidence | Meaning |
|------------|---------|
| 0.0 - 0.3 | Unlikely - weak signal |
| 0.3 - 0.5 | Possible - moderate signal |
| 0.5 - 0.8 | Likely - strong signal |
| 0.8 - 1.0 | Very likely - very strong signal |

### Severity Mapping

The system automatically maps confidence to severity labels:

| Confidence Range | Severity Label |
|------------------|----------------|
| ≥ 0.8 | **HIGH** |
| ≥ 0.5 | **MEDIUM** |
| ≥ 0.3 | **LOW** |
| < 0.3 | **NEGLIGIBLE** |

### Choosing Thresholds

**Lower threshold = More sensitive (more blocks, fewer false negatives)**
**Higher threshold = Less sensitive (fewer blocks, more permissive)**

Recommended starting points:

| Category Type | Strict | Moderate | Permissive |
|---------------|--------|----------|------------|
| Toxic/Profanity | 0.2 | 0.4 | 0.6 |
| Sexual | 0.2 | 0.3 | 0.5 |
| Violent | 0.3 | 0.4 | 0.6 |
| PII (Entity Salience) | 0.0 | 0.3 | 0.5 |
| Sentiment Score | -0.3 | -0.5 | -0.7 |

### Per-Category Thresholds

You can set different thresholds for different categories. This is useful when:
- Sexual content needs stricter filtering than violence
- You want to allow political content but block hate speech
- Different entity types need different salience thresholds

---

## Execution Modes

### Sequential vs Parallel

Each phase can run its functions in two modes:

| Mode | Description | Best For |
|------|-------------|----------|
| **Sequential** | Functions run one after another | Debugging, limited API quotas |
| **Parallel** | All functions run simultaneously | Production, lower latency |

### Performance Comparison

With 3 functions, each taking ~300ms:

| Mode | Total Time |
|------|------------|
| Sequential | ~900ms (300 × 3) |
| Parallel | ~300ms (slowest function) |

### When to Use Each

**Use Sequential when**:
- Debugging issues
- API quota is limited
- Order of execution matters
- You want predictable timing

**Use Parallel when**:
- Production environment
- Latency is critical
- Running multiple independent checks
- You have sufficient API quota

---

## Quick Start

### Minimal Setup

1. Place your GCP service account JSON in `secrets/guardrail_secret.json`
2. Create a `config.json` with your desired functions
3. Import and use the runner

### Basic Example

```python
from GCP_Guardrail_Runner import GuardrailRunner

# Initialize
runner = GuardrailRunner(config_path="config.json")

# Check input only
result = runner.run("Your text here")

# Check both input and output
result = runner.run("User prompt", generated_text="Model response")

# Check result
if result["summary"]["passed"]:
    print("Content is safe")
else:
    print("Content blocked:", result["summary"])
```

### Minimal Config

```json
{
  "input": {
    "functions": ["moderate_text", "model_armor"]
  }
}
```

---

## Output Structure

### Result Overview

Every call returns a dictionary with:

| Key | Description |
|-----|-------------|
| `input` | Results from input phase (if configured) |
| `output` | Results from output phase (if configured) |
| `total_time_seconds` | Total execution time |
| `summary` | Pass/fail status with failure details |
| `text` | Original input and generated text |

### Summary Structure

The summary tells you quickly if content passed or failed:

```
summary:
  passed: true/false          # Overall result
  input:
    passed: true/false        # Input phase result
    failures: [...]           # List of what failed (if any)
  output:
    passed: true/false        # Output phase result
    failures: [...]           # List of what failed (if any)
```

### Understanding Failures

Each failure includes:
- **function**: Which guardrail function caught it
- **category**: What category was triggered
- **confidence/salience**: The detected value
- **severity**: HIGH/MEDIUM/LOW/NEGLIGIBLE
- **reason**: Human-readable explanation (for sentiment)

### Timing Information

Each function and phase includes timing:
- Individual function: `time_taken_seconds`
- Phase total: `time_taken_seconds`
- Overall: `total_time_seconds`
- Execution mode: `execution_type` (sequential/parallel)

---

## Best Practices

### 1. Start Permissive, Then Tighten
Begin with higher thresholds (0.5-0.7) and lower them based on false negatives you observe.

### 2. Use Different Thresholds Per Phase
- Input phase: Stricter (catch malicious attempts)
- Output phase: May be slightly more permissive

### 3. Combine Functions Strategically
- Use `moderate_text` for content categories
- Use `model_armor` for AI-specific attacks
- Use `analyze_entities` for PII protection
- Use `analyze_sentiment` for tone control

### 4. Monitor and Tune
- Enable logging to track what's being blocked
- Review logs regularly to adjust thresholds
- Watch for false positives (legitimate content blocked)

### 5. Handle Errors Gracefully
- API errors don't crash the system
- Errors appear in results with details
- Consider what to do when a check fails to run

---

## Error Handling

The system handles errors gracefully without crashing:

| Error Type | Cause | What Happens |
|------------|-------|--------------|
| `InvalidArgument` | Bad input to API | Returns error in result |
| `PermissionDenied` | Credential issues | Returns error in result |
| `NotFound` | Bad template ID | Returns error in result |
| `ResourceExhausted` | API quota exceeded | Returns error in result |
| `ServiceUnavailable` | GCP outage | Returns error in result |

Errors appear in the summary failures and the individual function result.

---

## Logging

### Automatic Logging

When enabled, every query is logged to:
```
gcp_guardrail_log/{user_name}_{YYYY-MM-DD}.json
```

### What's Logged

- Timestamp of each query
- User name
- Input text
- Complete output result

### Accessing Logs

```python
# Get today's log file path
path = runner.get_log_file_path()

# Read all today's logs
logs = runner.get_logs()
```

### Disable Logging

Pass `enable_logging=False` when creating the runner.

---

*Last Updated: January 2026*
