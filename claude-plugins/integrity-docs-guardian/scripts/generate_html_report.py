#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate HTML email report from Guardian JSON report
Optimized for Codex GPT to receive actionable debugging context
"""

import json
import sys
import os

# Fix encoding for Windows
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def escape_html(text):
    """Escape HTML special characters"""
    if not text:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def generate_html_report(report):
    """
    Generate rich HTML report from JSON report
    Returns: HTML string
    """

    # Status colors
    status_colors = {"OK": "#44ff44", "DEGRADED": "#ffaa00", "CRITICAL": "#ff4444"}
    status_color = status_colors.get(report["status"], "#4a9eff")

    # Build HTML
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Guardian Report - EMERGENCE V8</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            background-color: #0a0e27;
            color: #e0e0e0;
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background-color: #1a1f3a;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }}
        h1 {{
            color: #ffffff;
            margin-top: 0;
            border-bottom: 3px solid {status_color};
            padding-bottom: 15px;
        }}
        .status-badge {{
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 14px;
            background-color: {status_color};
            color: #ffffff;
            margin-bottom: 20px;
        }}
        .summary-box {{
            background-color: #252b4a;
            border-left: 4px solid {status_color};
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .summary-item {{
            background-color: #1a1f3a;
            padding: 15px;
            border-radius: 6px;
            text-align: center;
        }}
        .summary-item .number {{
            font-size: 32px;
            font-weight: bold;
            color: {status_color};
        }}
        .summary-item .label {{
            font-size: 12px;
            color: #a0a0a0;
            text-transform: uppercase;
            margin-top: 5px;
        }}
        .section {{
            margin: 30px 0;
        }}
        .section-title {{
            font-size: 20px;
            color: #4a9eff;
            border-bottom: 2px solid #2a3f5f;
            padding-bottom: 10px;
            margin-bottom: 15px;
        }}
        .error-card {{
            background-color: #2a1f1f;
            border-left: 4px solid #ff4444;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 15px;
        }}
        .code-block {{
            background-color: #0d1117;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 16px;
            overflow-x: auto;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 13px;
            margin: 10px 0;
            color: #c9d1d9;
        }}
        .code-block pre {{
            margin: 0;
            white-space: pre-wrap;
        }}
        .endpoint-tag {{
            display: inline-block;
            background-color: #3a3f5a;
            color: #4a9eff;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-family: monospace;
            margin: 5px 5px 5px 0;
        }}
        .file-tag {{
            display: inline-block;
            background-color: #3a3f5a;
            color: #ffaa00;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-family: monospace;
            margin: 5px 5px 5px 0;
        }}
        .error-type-tag {{
            display: inline-block;
            background-color: #3a3f5a;
            color: #ff4444;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-family: monospace;
            margin: 5px 5px 5px 0;
        }}
        .recommendation {{
            background-color: #252b4a;
            border-left: 4px solid #4a9eff;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 15px;
        }}
        .recommendation.high {{
            border-left-color: #ff4444;
        }}
        .recommendation.medium {{
            border-left-color: #ffaa00;
        }}
        .recommendation.low {{
            border-left-color: #44ff44;
        }}
        .command {{
            background-color: #0d1117;
            border: 1px solid #30363d;
            padding: 10px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 12px;
            margin-top: 10px;
            color: #4a9eff;
        }}
        .timestamp {{
            color: #a0a0a0;
            font-size: 12px;
        }}
        .commit {{
            background-color: #252b4a;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 10px;
            font-size: 13px;
        }}
        .commit .hash {{
            color: #4a9eff;
            font-family: monospace;
        }}
        .commit .author {{
            color: #ffaa00;
        }}
        .pattern-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .pattern-box {{
            background-color: #252b4a;
            padding: 15px;
            border-radius: 6px;
        }}
        .pattern-box h4 {{
            margin-top: 0;
            color: #4a9eff;
            font-size: 14px;
        }}
        .pattern-item {{
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
            border-bottom: 1px solid #2a3f5f;
        }}
        .pattern-item:last-child {{
            border-bottom: none;
        }}
        .badge-count {{
            background-color: #ff4444;
            color: white;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: bold;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #2a3f5f;
            text-align: center;
            color: #a0a0a0;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🛡️ Guardian Report - EMERGENCE V8</h1>

        <div class="status-badge">{report["status"]}</div>

        <div class="summary-box">
            <h3 style="margin-top: 0;">📊 Summary</h3>
            <p><strong>Service:</strong> {report["service"]} ({report["region"]})</p>
            <p><strong>Timestamp:</strong> <span class="timestamp">{report["timestamp"]}</span></p>
            <p><strong>Logs analyzed:</strong> {report["logs_analyzed"]} (last {report["freshness"]})</p>

            <div class="summary-grid">
                <div class="summary-item">
                    <div class="number">{report["summary"]["errors"]}</div>
                    <div class="label">Errors</div>
                </div>
                <div class="summary-item">
                    <div class="number">{report["summary"]["warnings"]}</div>
                    <div class="label">Warnings</div>
                </div>
                <div class="summary-item">
                    <div class="number">{report["summary"]["critical_signals"]}</div>
                    <div class="label">Critical Signals</div>
                </div>
                <div class="summary-item">
                    <div class="number">{report["summary"]["latency_issues"]}</div>
                    <div class="label">Latency Issues</div>
                </div>
            </div>
        </div>
"""

    # Error Patterns Analysis
    if report.get("error_patterns"):
        patterns = report["error_patterns"]
        if (
            patterns.get("by_endpoint")
            or patterns.get("by_error_type")
            or patterns.get("by_file")
        ):
            html += """
        <div class="section">
            <h2 class="section-title">🔍 Error Patterns Analysis</h2>
            <div class="pattern-grid">
"""

            if patterns.get("by_endpoint"):
                html += """
                <div class="pattern-box">
                    <h4>🌐 By Endpoint</h4>
"""
                for endpoint, count in list(patterns["by_endpoint"].items())[
                    :5
                ]:  # Top 5
                    html += f"""
                    <div class="pattern-item">
                        <span class="endpoint-tag">{escape_html(endpoint)}</span>
                        <span class="badge-count">{count}</span>
                    </div>
"""
                html += """
                </div>
"""

            if patterns.get("by_error_type"):
                html += """
                <div class="pattern-box">
                    <h4>⚠️ By Error Type</h4>
"""
                for error_type, count in list(patterns["by_error_type"].items())[
                    :5
                ]:  # Top 5
                    html += f"""
                    <div class="pattern-item">
                        <span class="error-type-tag">{escape_html(error_type)}</span>
                        <span class="badge-count">{count}</span>
                    </div>
"""
                html += """
                </div>
"""

            if patterns.get("by_file"):
                html += """
                <div class="pattern-box">
                    <h4>📁 By File</h4>
"""
                for file_path, count in list(patterns["by_file"].items())[:5]:  # Top 5
                    html += f"""
                    <div class="pattern-item">
                        <span class="file-tag">{escape_html(file_path)}</span>
                        <span class="badge-count">{count}</span>
                    </div>
"""
                html += """
                </div>
"""

            html += """
            </div>
        </div>
"""

    # Detailed Errors
    if report.get("errors_detailed"):
        html += f"""
        <div class="section">
            <h2 class="section-title">❌ Detailed Errors (Top {len(report["errors_detailed"])})</h2>
"""

        for error in report["errors_detailed"]:
            html += """
            <div class="error-card">
"""
            html += f"""
                <p><strong>⏰ Time:</strong> <span class="timestamp">{escape_html(error.get("timestamp", ""))}</span></p>
                <p><strong>🔴 Severity:</strong> {escape_html(error.get("severity", "UNKNOWN"))}</p>
"""

            if error.get("endpoint"):
                method = error.get("http_method", "")
                html += f"""
                <p><strong>🌐 Endpoint:</strong> <span class="endpoint-tag">{escape_html(method)} {escape_html(error["endpoint"])}</span></p>
"""

            if error.get("error_type"):
                html += f"""
                <p><strong>⚠️ Type:</strong> <span class="error-type-tag">{escape_html(error["error_type"])}</span></p>
"""

            if error.get("file_path"):
                line = error.get("line_number", "")
                html += f"""
                <p><strong>📁 File:</strong> <span class="file-tag">{escape_html(error["file_path"])}:{line}</span></p>
"""

            html += f"""
                <p><strong>💬 Message:</strong></p>
                <div class="code-block">
                    <pre>{escape_html(error.get("message", ""))}</pre>
                </div>
"""

            if error.get("stack_trace"):
                html += f"""
                <p><strong>📚 Stack Trace:</strong></p>
                <div class="code-block">
                    <pre>{escape_html(error["stack_trace"])}</pre>
                </div>
"""

            if error.get("request_id"):
                html += f"""
                <p><strong>🔍 Request ID:</strong> <code>{escape_html(error["request_id"])}</code> (for tracing)</p>
"""

            html += """
            </div>
"""

        html += """
        </div>
"""

    # Code Snippets
    if report.get("code_snippets"):
        html += """
        <div class="section">
            <h2 class="section-title">💻 Suspect Code Snippets</h2>
"""

        for snippet in report["code_snippets"]:
            error_count = snippet.get("error_count", 0)
            html += f"""
            <div class="pattern-box">
                <h4>📁 {escape_html(snippet["file"])} <span style="color: #ff4444;">({error_count} errors)</span></h4>
                <p style="font-size: 12px; color: #a0a0a0;">Line {snippet["line"]} (showing lines {snippet["start_line"]}-{snippet["end_line"]})</p>
                <div class="code-block">
                    <pre>{escape_html(snippet["code_snippet"])}</pre>
                </div>
            </div>
"""

        html += """
        </div>
"""

    # Recent Commits
    if report.get("recent_commits"):
        html += """
        <div class="section">
            <h2 class="section-title">🔀 Recent Commits (Potential Culprits)</h2>
"""

        for commit in report["recent_commits"]:
            html += f"""
            <div class="commit">
                <span class="hash">{escape_html(commit["hash"])}</span> by <span class="author">{escape_html(commit["author"])}</span> <span class="timestamp">({escape_html(commit["time"])})</span>
                <p style="margin: 5px 0 0 0;">{escape_html(commit["message"])}</p>
            </div>
"""

        html += """
        </div>
"""

    # Recommendations
    if report.get("recommendations"):
        html += """
        <div class="section">
            <h2 class="section-title">💡 Recommendations</h2>
"""

        for rec in report["recommendations"]:
            priority = rec.get("priority", "MEDIUM")
            priority_class = priority.lower()
            html += f"""
            <div class="recommendation {priority_class}">
                <p><strong>🚨 [{escape_html(priority)}] {escape_html(rec.get("action", ""))}</strong></p>
                <p>{escape_html(rec.get("details", ""))}</p>
"""

            if rec.get("command"):
                html += f"""
                <p><strong>Command:</strong></p>
                <div class="command">{escape_html(rec["command"])}</div>
"""

            if rec.get("rollback_command"):
                html += f"""
                <p><strong>Rollback Command:</strong></p>
                <div class="command">{escape_html(rec["rollback_command"])}</div>
"""

            if rec.get("suggested_fix"):
                html += f"""
                <p><strong>Suggested Fix:</strong> {escape_html(rec["suggested_fix"])}</p>
"""

            if rec.get("affected_endpoints"):
                html += """
                <p><strong>Affected Endpoints:</strong></p>
"""
                for endpoint in rec["affected_endpoints"]:
                    html += f"""
                <span class="endpoint-tag">{escape_html(endpoint)}</span>
"""

            if rec.get("affected_files"):
                html += """
                <p><strong>Affected Files:</strong></p>
"""
                for file_path in rec["affected_files"]:
                    html += f"""
                <span class="file-tag">{escape_html(file_path)}</span>
"""

            if rec.get("suggested_investigation"):
                html += """
                <p><strong>Investigation Steps:</strong></p>
                <ul>
"""
                for step in rec["suggested_investigation"]:
                    html += f"""
                    <li>{escape_html(step)}</li>
"""
                html += """
                </ul>
"""

            html += """
            </div>
"""

        html += """
        </div>
"""

    # Footer
    html += f"""
        <div class="footer">
            <p>🤖 Guardian System 3.0.0 - Automated Production Monitoring</p>
            <p>ÉMERGENCE V8 Production Monitoring | Generated {report["timestamp"]}</p>
            <p style="margin-top: 10px; font-size: 11px;">
                This report is optimized for Codex GPT to take actionable debugging steps.<br>
                All context (stack traces, code snippets, patterns) is included for autonomous troubleshooting.
            </p>
        </div>
    </div>
</body>
</html>
"""

    return html


def main():
    """Main execution"""
    if len(sys.argv) < 2:
        print(
            "Usage: python generate_html_report.py <path_to_json_report>",
            file=sys.stderr,
        )
        sys.exit(1)

    json_path = sys.argv[1]

    if not os.path.exists(json_path):
        print(f"Error: File not found: {json_path}", file=sys.stderr)
        sys.exit(1)

    # Load JSON report
    with open(json_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    # Generate HTML
    html = generate_html_report(report)

    # Output to stdout (can be redirected to file)
    print(html)


if __name__ == "__main__":
    main()
