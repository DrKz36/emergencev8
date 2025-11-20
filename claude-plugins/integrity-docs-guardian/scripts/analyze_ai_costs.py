#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Theia (CostWatcher) - AI Model Cost Analyzer
Scans codebase for AI model usage and recommends cost optimizations
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8") if hasattr(
        sys.stdout, "reconfigure"
    ) else None

# Configuration
SCRIPT_DIR = Path(__file__).parent
PLUGIN_DIR = SCRIPT_DIR.parent
REPO_ROOT = PLUGIN_DIR.parent.parent
REPORTS_DIR = REPO_ROOT / "reports"  # UNIFIED: All reports in repo root
CONFIG_DIR = PLUGIN_DIR / "config"

# Ensure directories exist
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class ModelPricing:
    """Pricing information for an AI model"""

    model: str
    provider: str
    input_cost_per_1k: float  # USD per 1k tokens
    output_cost_per_1k: float  # USD per 1k tokens
    context_window: int
    released: str  # YYYY-MM-DD
    status: str  # current, deprecated, experimental


@dataclass
class ModelUsage:
    """Detected usage of an AI model in codebase"""

    model: str
    provider: str
    file_path: str
    line_number: int
    context: str  # Surrounding code


@dataclass
class CostRecommendation:
    """Recommendation for cost optimization"""

    current_model: str
    current_provider: str
    suggested_model: str
    suggested_provider: str
    reason: str
    cost_change_percent: float
    monthly_savings: float  # USD (negative = additional cost)
    performance_delta: int  # -100 to +100
    priority: str  # HIGH, MEDIUM, LOW
    action: str  # UPGRADE, DOWNGRADE, SWITCH, EVALUATE, KEEP


# Latest pricing database (as of January 2025)
PRICING_DATABASE = {
    "openai": {
        "gpt-4o": ModelPricing(
            model="gpt-4o",
            provider="openai",
            input_cost_per_1k=2.50,
            output_cost_per_1k=10.00,
            context_window=128000,
            released="2024-05-13",
            status="current",
        ),
        "gpt-4o-mini": ModelPricing(
            model="gpt-4o-mini",
            provider="openai",
            input_cost_per_1k=0.15,
            output_cost_per_1k=0.60,
            context_window=128000,
            released="2024-07-18",
            status="current",
        ),
        "gpt-4-turbo": ModelPricing(
            model="gpt-4-turbo",
            provider="openai",
            input_cost_per_1k=10.00,
            output_cost_per_1k=30.00,
            context_window=128000,
            released="2024-04-09",
            status="current",
        ),
        "gpt-3.5-turbo": ModelPricing(
            model="gpt-3.5-turbo",
            provider="openai",
            input_cost_per_1k=0.50,
            output_cost_per_1k=1.50,
            context_window=16385,
            released="2023-03-01",
            status="deprecated",
        ),
        "text-embedding-3-small": ModelPricing(
            model="text-embedding-3-small",
            provider="openai",
            input_cost_per_1k=0.02,
            output_cost_per_1k=0.00,
            context_window=8191,
            released="2024-01-25",
            status="current",
        ),
        "text-embedding-3-large": ModelPricing(
            model="text-embedding-3-large",
            provider="openai",
            input_cost_per_1k=0.13,
            output_cost_per_1k=0.00,
            context_window=8191,
            released="2024-01-25",
            status="current",
        ),
    },
    "google": {
        "gemini-1.5-pro": ModelPricing(
            model="gemini-1.5-pro",
            provider="google",
            input_cost_per_1k=1.25,
            output_cost_per_1k=5.00,
            context_window=2000000,
            released="2024-05-14",
            status="current",
        ),
        "gemini-1.5-flash": ModelPricing(
            model="gemini-1.5-flash",
            provider="google",
            input_cost_per_1k=0.075,
            output_cost_per_1k=0.30,
            context_window=1000000,
            released="2024-05-14",
            status="current",
        ),
        "gemini-2.0-flash-exp": ModelPricing(
            model="gemini-2.0-flash-exp",
            provider="google",
            input_cost_per_1k=0.00,  # Free during preview
            output_cost_per_1k=0.00,
            context_window=1000000,
            released="2024-12-11",
            status="experimental",
        ),
        "text-embedding-004": ModelPricing(
            model="text-embedding-004",
            provider="google",
            input_cost_per_1k=0.00,  # Free
            output_cost_per_1k=0.00,
            context_window=2048,
            released="2024-09-24",
            status="current",
        ),
    },
    "anthropic": {
        "claude-3-5-sonnet-20241022": ModelPricing(
            model="claude-3-5-sonnet-20241022",
            provider="anthropic",
            input_cost_per_1k=3.00,
            output_cost_per_1k=15.00,
            context_window=200000,
            released="2024-10-22",
            status="current",
        ),
        "claude-3-5-haiku-20241022": ModelPricing(
            model="claude-3-5-haiku-20241022",
            provider="anthropic",
            input_cost_per_1k=0.80,
            output_cost_per_1k=4.00,
            context_window=200000,
            released="2024-11-04",
            status="current",
        ),
        "claude-3-opus-20240229": ModelPricing(
            model="claude-3-opus-20240229",
            provider="anthropic",
            input_cost_per_1k=15.00,
            output_cost_per_1k=75.00,
            context_window=200000,
            released="2024-02-29",
            status="current",
        ),
        "claude-3-sonnet-20240229": ModelPricing(
            model="claude-3-sonnet-20240229",
            provider="anthropic",
            input_cost_per_1k=3.00,
            output_cost_per_1k=15.00,
            context_window=200000,
            released="2024-02-29",
            status="deprecated",
        ),
        "claude-3-haiku-20240307": ModelPricing(
            model="claude-3-haiku-20240307",
            provider="anthropic",
            input_cost_per_1k=0.25,
            output_cost_per_1k=1.25,
            context_window=200000,
            released="2024-03-07",
            status="deprecated",
        ),
    },
}


# Model patterns to search for in code
MODEL_PATTERNS = [
    # Direct model assignments
    r'model\s*[=:]\s*["\']([^"\']+)["\']',
    r'engine\s*[=:]\s*["\']([^"\']+)["\']',
    r'provider\s*[=:]\s*["\']([^"\']+)["\']',
    # Environment variables
    r'OPENAI_MODEL["\']?\s*[=:]\s*["\']([^"\']+)["\']',
    r'GEMINI_MODEL["\']?\s*[=:]\s*["\']([^"\']+)["\']',
    r'ANTHROPIC_MODEL["\']?\s*[=:]\s*["\']([^"\']+)["\']',
    r'AI_MODEL["\']?\s*[=:]\s*["\']([^"\']+)["\']',
    # Model names directly
    r"(gpt-[34][-.a-z0-9]*)",
    r"(gemini-[12][-.a-z0-9]*)",
    r"(claude-[23][-.a-z0-9]*)",
    r"(text-embedding-[-.a-z0-9]+)",
]


def scan_codebase() -> List[ModelUsage]:
    """Scan codebase for AI model usage"""
    print("🔍 Scanning codebase for AI model usage...")

    usages = []
    scan_paths = [
        REPO_ROOT / "src" / "backend",
        REPO_ROOT / "src" / "frontend",
        REPO_ROOT / ".env",
        REPO_ROOT / ".env.local",
        REPO_ROOT / "config",
    ]

    file_patterns = [
        "*.py",
        "*.js",
        "*.ts",
        "*.jsx",
        "*.tsx",
        "*.json",
        "*.yaml",
        "*.yml",
        ".env*",
    ]
    exclude_patterns = ["node_modules", ".venv", "venv", "__pycache__", "*.pyc"]

    files_scanned = 0
    models_found = set()

    for scan_path in scan_paths:
        if not scan_path.exists():
            continue

        for pattern in file_patterns:
            for file_path in scan_path.rglob(
                pattern if "*" in pattern else f"**/{pattern}"
            ):
                # Skip excluded directories
                if any(excl in str(file_path) for excl in exclude_patterns):
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        lines = content.split("\n")

                        for line_num, line in enumerate(lines, 1):
                            for pattern in MODEL_PATTERNS:
                                matches = re.finditer(pattern, line, re.IGNORECASE)
                                for match in matches:
                                    model_name = match.group(1)

                                    # Determine provider
                                    provider = detect_provider(model_name)
                                    if not provider:
                                        continue

                                    # Get context (3 lines before and after)
                                    start = max(0, line_num - 3)
                                    end = min(len(lines), line_num + 3)
                                    context = "\n".join(lines[start:end])

                                    usage = ModelUsage(
                                        model=model_name,
                                        provider=provider,
                                        file_path=str(file_path.relative_to(REPO_ROOT)),
                                        line_number=line_num,
                                        context=context[:200],  # Limit context length
                                    )
                                    usages.append(usage)
                                    models_found.add(f"{provider}:{model_name}")

                    files_scanned += 1

                except Exception as e:
                    print(f"   ⚠️  Error reading {file_path}: {e}")

    print(f"   ✅ Scanned {files_scanned} files")
    print(f"   ✅ Found {len(models_found)} unique model(s): {', '.join(models_found)}")
    print(f"   ✅ Total {len(usages)} usage location(s)\n")

    return usages


def detect_provider(model_name: str) -> Optional[str]:
    """Detect provider from model name"""
    model_lower = model_name.lower()

    if "gpt" in model_lower or "text-embedding" in model_lower:
        return "openai"
    elif "gemini" in model_lower:
        return "google"
    elif "claude" in model_lower:
        return "anthropic"

    return None


def get_pricing(model: str, provider: str) -> Optional[ModelPricing]:
    """Get pricing for a model"""
    if provider in PRICING_DATABASE:
        # Try exact match first
        if model in PRICING_DATABASE[provider]:
            return PRICING_DATABASE[provider][model]

        # Try fuzzy match (e.g., "gpt-4o" matches "gpt-4o-2024-05-13")
        for db_model, pricing in PRICING_DATABASE[provider].items():
            if model.startswith(db_model) or db_model.startswith(model):
                return pricing

    return None


def analyze_costs(usages: List[ModelUsage]) -> Tuple[Dict, List[CostRecommendation]]:
    """Analyze costs and generate recommendations"""
    print("💰 Analyzing costs and generating recommendations...\n")

    # Group usages by model
    models_by_usage = defaultdict(list)
    for usage in usages:
        models_by_usage[f"{usage.provider}:{usage.model}"].append(usage)

    current_models = []
    recommendations = []

    # Default usage estimation (can be overridden with real data)
    # Realistic values based on actual usage (~80 CHF/month)
    DEFAULT_MONTHLY_REQUESTS = 200  # ~200 requests/month
    DEFAULT_INPUT_TOKENS = 400  # ~400 tokens per request
    DEFAULT_OUTPUT_TOKENS = 300  # ~300 tokens per request

    for model_key, model_usages in models_by_usage.items():
        provider, model = model_key.split(":")
        pricing = get_pricing(model, provider)

        if not pricing:
            print(f"   ⚠️  No pricing data for {model_key}, skipping...")
            continue

        # Estimate monthly cost
        monthly_cost = calculate_monthly_cost(
            pricing,
            DEFAULT_MONTHLY_REQUESTS,
            DEFAULT_INPUT_TOKENS,
            DEFAULT_OUTPUT_TOKENS,
        )

        current_model_info = {
            "model": model,
            "provider": provider,
            "usage_locations": [f"{u.file_path}:{u.line_number}" for u in model_usages],
            "count": len(model_usages),
            "current_cost": {
                "input_per_1k": pricing.input_cost_per_1k,
                "output_per_1k": pricing.output_cost_per_1k,
            },
            "estimated_monthly_volume": {
                "requests": DEFAULT_MONTHLY_REQUESTS,
                "input_tokens": DEFAULT_MONTHLY_REQUESTS * DEFAULT_INPUT_TOKENS,
                "output_tokens": DEFAULT_MONTHLY_REQUESTS * DEFAULT_OUTPUT_TOKENS,
            },
            "estimated_monthly_cost": round(monthly_cost, 2),
            "context_window": pricing.context_window,
            "status": pricing.status,
        }
        current_models.append(current_model_info)

        # Find better alternatives
        alt_recommendations = find_alternatives(pricing, monthly_cost)
        recommendations.extend(alt_recommendations)

    # Sort recommendations by savings (descending)
    recommendations.sort(key=lambda x: x.monthly_savings, reverse=True)

    summary = {
        "models_analyzed": len(current_models),
        "total_monthly_cost": round(
            sum(m["estimated_monthly_cost"] for m in current_models), 2
        ),
        "potential_savings": round(
            sum(r.monthly_savings for r in recommendations if r.monthly_savings > 0), 2
        ),
        "high_priority_count": len(
            [r for r in recommendations if r.priority == "HIGH"]
        ),
        "deprecated_models": len(
            [m for m in current_models if m["status"] == "deprecated"]
        ),
    }

    print(f"   ✅ Analyzed {summary['models_analyzed']} model(s)")
    print(f"   💵 Total monthly cost: ${summary['total_monthly_cost']}")
    print(f"   💰 Potential savings: ${summary['potential_savings']}")
    print(f"   🔴 High priority recommendations: {summary['high_priority_count']}")
    print(f"   ⚠️  Deprecated models: {summary['deprecated_models']}\n")

    return {"summary": summary, "current_models": current_models}, recommendations


def calculate_monthly_cost(
    pricing: ModelPricing,
    monthly_requests: int,
    avg_input_tokens: int,
    avg_output_tokens: int,
) -> float:
    """Calculate estimated monthly cost"""
    total_input_tokens = monthly_requests * avg_input_tokens
    total_output_tokens = monthly_requests * avg_output_tokens

    input_cost = (total_input_tokens / 1000) * pricing.input_cost_per_1k
    output_cost = (total_output_tokens / 1000) * pricing.output_cost_per_1k

    return input_cost + output_cost


def find_alternatives(
    current: ModelPricing, current_monthly_cost: float
) -> List[CostRecommendation]:
    """Find alternative models with better cost/performance"""
    recommendations = []
    seen_alternatives = set()  # Track alternatives to avoid duplicates
    max_recommendations = 5  # Limit to top 5 alternatives per model

    # Search all providers for alternatives
    for provider, models in PRICING_DATABASE.items():
        for alt_model, alt_pricing in models.items():
            # Skip same model
            if alt_model == current.model and provider == current.provider:
                continue

            # Skip if we've already recommended this alternative
            alt_key = f"{provider}:{alt_model}"
            if alt_key in seen_alternatives:
                continue
            seen_alternatives.add(alt_key)

            # Skip experimental models for production use
            if alt_pricing.status == "experimental":
                continue

            # Calculate alternative cost (use realistic usage)
            alt_monthly_cost = calculate_monthly_cost(
                alt_pricing,
                200,  # Realistic monthly requests
                400,  # Realistic input tokens
                300,  # Realistic output tokens
            )

            savings = current_monthly_cost - alt_monthly_cost
            cost_change_percent = (
                ((alt_monthly_cost - current_monthly_cost) / current_monthly_cost) * 100
                if current_monthly_cost > 0
                else 0
            )

            # Only recommend if there's a significant difference
            if abs(cost_change_percent) < 5:
                continue

            # Determine action and priority
            if savings > 0:
                action = "SWITCH" if provider != current.provider else "DOWNGRADE"
                if cost_change_percent < -30:
                    priority = "HIGH"
                elif cost_change_percent < -15:
                    priority = "MEDIUM"
                else:
                    priority = "LOW"
                reason = f"{abs(cost_change_percent):.0f}% cost reduction"
            else:
                action = "UPGRADE" if provider == current.provider else "EVALUATE"
                priority = "LOW"
                reason = f"Better performance (context: {alt_pricing.context_window} vs {current.context_window})"

            # Add bonus for deprecated models
            if current.status == "deprecated":
                priority = "HIGH"
                reason = f"Current model deprecated - {reason}"

            recommendation = CostRecommendation(
                current_model=current.model,
                current_provider=current.provider,
                suggested_model=alt_model,
                suggested_provider=provider,
                reason=reason,
                cost_change_percent=round(cost_change_percent, 1),
                monthly_savings=round(savings, 2),
                performance_delta=estimate_performance_delta(current, alt_pricing),
                priority=priority,
                action=action,
            )
            recommendations.append(recommendation)

    # Sort by savings and return top recommendations
    recommendations.sort(key=lambda x: x.monthly_savings, reverse=True)
    return recommendations[:max_recommendations]


def estimate_performance_delta(current: ModelPricing, alternative: ModelPricing) -> int:
    """Estimate performance difference (-100 to +100)"""
    # Simple heuristic based on context window and price
    context_ratio = (alternative.context_window / current.context_window - 1) * 50
    price_ratio = (
        (alternative.input_cost_per_1k + alternative.output_cost_per_1k)
        / (current.input_cost_per_1k + current.output_cost_per_1k)
        - 1
    ) * 30

    delta = int(context_ratio + price_ratio)
    return max(-100, min(100, delta))


def generate_reports(
    analysis: Dict, recommendations: List[CostRecommendation]
) -> Tuple[str, str]:
    """Generate Markdown and JSON reports"""
    timestamp = datetime.now()
    date_str = timestamp.strftime("%Y%m%d")

    # Filenames
    md_file = REPORTS_DIR / f"ai_model_cost_audit_{date_str}.md"
    json_file = REPORTS_DIR / f"ai_model_cost_audit_{date_str}.json"

    # Generate Markdown report
    md_content = generate_markdown_report(analysis, recommendations, timestamp)
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(md_content)

    # Generate JSON report
    json_content = {
        "timestamp": timestamp.isoformat(),
        **analysis,
        "recommendations": [asdict(r) for r in recommendations],
    }
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_content, f, indent=2)

    return str(md_file), str(json_file)


def generate_markdown_report(
    analysis: Dict, recommendations: List[CostRecommendation], timestamp: datetime
) -> str:
    """Generate Markdown report content"""
    summary = analysis["summary"]
    current_models = analysis["current_models"]

    md = f"""# 💰 Theia (CostWatcher) - AI Model Cost Audit

**Date:** {timestamp.strftime("%Y-%m-%d %H:%M:%S")}
**Agent:** Theia (CostWatcher)
**Status:** {"🟢 OPTIMIZED" if summary["potential_savings"] < 100 else "🟡 OPTIMIZATION AVAILABLE" if summary["potential_savings"] < 500 else "🔴 HIGH SAVINGS POTENTIAL"}

---

## 📊 Executive Summary

- **Models Analyzed:** {summary["models_analyzed"]}
- **Total Monthly Cost:** ${summary["total_monthly_cost"]:.2f}
- **Potential Savings:** ${summary["potential_savings"]:.2f}
- **Optimization Score:** {100 - int((summary["potential_savings"] / max(summary["total_monthly_cost"], 1)) * 100)}/100
- **High Priority Recommendations:** {summary["high_priority_count"]}
- **Deprecated Models:** {summary["deprecated_models"]}

"""

    if summary["potential_savings"] > 100:
        md += f"""
### 🎯 Key Opportunity
**You could save ${summary["potential_savings"]:.2f}/month ({(summary["potential_savings"] / summary["total_monthly_cost"] * 100):.1f}%) by optimizing model usage!**

"""

    md += """---

## 📋 Current Models

| Model | Provider | Input Cost | Output Cost | Monthly Cost | Locations | Status |
|-------|----------|------------|-------------|--------------|-----------|--------|
"""

    for model in current_models:
        status_emoji = (
            "✅"
            if model["status"] == "current"
            else "⚠️"
            if model["status"] == "deprecated"
            else "🧪"
        )
        md += f"| {model['model']} | {model['provider']} | ${model['current_cost']['input_per_1k']:.2f} | ${model['current_cost']['output_per_1k']:.2f} | ${model['estimated_monthly_cost']:.2f} | {model['count']} | {status_emoji} {model['status']} |\n"

    md += """
---

## 💡 Optimization Recommendations

"""

    if not recommendations:
        md += "_No optimization opportunities detected at this time._\n"
    else:
        # Group by priority
        high_priority = [r for r in recommendations if r.priority == "HIGH"]
        medium_priority = [r for r in recommendations if r.priority == "MEDIUM"]
        low_priority = [r for r in recommendations if r.priority == "LOW"]

        if high_priority:
            md += "### 🔴 HIGH Priority\n\n"
            md += "| Current | Suggested | Provider | Savings | Impact | Action |\n"
            md += "|---------|-----------|----------|---------|--------|--------|\n"
            for rec in high_priority:
                savings_emoji = "💰" if rec.monthly_savings > 0 else "📈"
                md += f"| {rec.current_model} | {rec.suggested_model} | {rec.suggested_provider} | {savings_emoji} ${abs(rec.monthly_savings):.2f}/mo ({rec.cost_change_percent:+.1f}%) | {rec.reason} | {rec.action} |\n"
            md += "\n"

        if medium_priority:
            md += "### 🟡 MEDIUM Priority\n\n"
            md += "| Current | Suggested | Provider | Savings | Impact | Action |\n"
            md += "|---------|-----------|----------|---------|--------|--------|\n"
            for rec in medium_priority:
                savings_emoji = "💰" if rec.monthly_savings > 0 else "📈"
                md += f"| {rec.current_model} | {rec.suggested_model} | {rec.suggested_provider} | {savings_emoji} ${abs(rec.monthly_savings):.2f}/mo ({rec.cost_change_percent:+.1f}%) | {rec.reason} | {rec.action} |\n"
            md += "\n"

        if low_priority:
            md += "### 🟢 LOW Priority\n\n"
            md += "<details>\n<summary>Click to expand low priority recommendations</summary>\n\n"
            md += "| Current | Suggested | Provider | Savings | Impact | Action |\n"
            md += "|---------|-----------|----------|---------|--------|--------|\n"
            for rec in low_priority:
                savings_emoji = "💰" if rec.monthly_savings > 0 else "📈"
                md += f"| {rec.current_model} | {rec.suggested_model} | {rec.suggested_provider} | {savings_emoji} ${abs(rec.monthly_savings):.2f}/mo ({rec.cost_change_percent:+.1f}%) | {rec.reason} | {rec.action} |\n"
            md += "\n</details>\n\n"

    md += """---

## 📍 Usage Locations

"""

    for model in current_models:
        md += f"### {model['provider']}: {model['model']}\n\n"
        for location in model["usage_locations"]:
            md += f"- `{location}`\n"
        md += "\n"

    md += f"""---

## 📚 Notes

- **Estimation baseline:** 200 requests/month, 400 input tokens, 300 output tokens per request
- **Pricing updated:** January 2025
- **Sources:**
  - [OpenAI Pricing](https://platform.openai.com/docs/pricing)
  - [Google AI Pricing](https://ai.google.dev/gemini-api/docs/pricing)
  - [Anthropic Pricing](https://www.anthropic.com/api#pricing)

---

**Generated by Theia (CostWatcher) - ÉMERGENCE Guardian**
**Report:** `{REPORTS_DIR / f"ai_model_cost_audit_{timestamp.strftime('%Y%m%d')}.json"}`
"""

    return md


def main():
    """Main execution"""
    print("=" * 70)
    print("  💰 Theia (CostWatcher) - AI Model Cost Analyzer")
    print("=" * 70)
    print()

    # Step 1: Scan codebase
    usages = scan_codebase()

    if not usages:
        print("⚠️  No AI models found in codebase. Exiting.")
        return 0

    # Step 2: Analyze costs
    analysis, recommendations = analyze_costs(usages)

    # Step 3: Generate reports
    print("📝 Generating reports...")
    md_file, json_file = generate_reports(analysis, recommendations)
    print(f"   ✅ Markdown report: {md_file}")
    print(f"   ✅ JSON report: {json_file}")
    print()

    # Summary
    summary = analysis["summary"]
    print("=" * 70)
    print("  📊 ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"  Models analyzed: {summary['models_analyzed']}")
    print(f"  Total monthly cost: ${summary['total_monthly_cost']:.2f}")
    print(f"  Potential savings: ${summary['potential_savings']:.2f}")
    print(f"  High priority actions: {summary['high_priority_count']}")
    print()

    if summary["potential_savings"] > 100:
        print(f"  🎯 You could save ${summary['potential_savings']:.2f}/month!")
        print(f"  📋 Review report: {md_file}")
        print()

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  Analysis interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
