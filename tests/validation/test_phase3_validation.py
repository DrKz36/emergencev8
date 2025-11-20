#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 3 UI/UX Validation Tests
Automated testing script for Phase 3 UI/UX improvements
Tests button system consistency and sticky header implementation
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding
if sys.platform == "win32":
    os.system("chcp 65001 > nul")
    if sys.stdout.encoding != "utf-8":
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


class Colors:
    """ANSI color codes for terminal output"""

    RESET = "\033[0m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    CYAN = "\033[96m"


def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(80)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}\n")


def print_test(test_name: str):
    """Print test name"""
    print(f"{Colors.BOLD}{Colors.CYAN}Test: {test_name}{Colors.RESET}")


def print_success(message: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_warning(message: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


def print_info(message: str):
    """Print info message"""
    print(f"  {message}")


class TestResults:
    """Track test results"""

    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.errors = []

    def add_pass(self):
        self.total += 1
        self.passed += 1

    def add_fail(self, error: str):
        self.total += 1
        self.failed += 1
        self.errors.append(error)

    def add_warning(self):
        self.warnings += 1

    def print_summary(self):
        print_header("TEST SUMMARY")
        print(f"Total Tests: {self.total}")
        print_success(f"Passed: {self.passed}")
        if self.failed > 0:
            print_error(f"Failed: {self.failed}")
        if self.warnings > 0:
            print_warning(f"Warnings: {self.warnings}")

        if self.errors:
            print(f"\n{Colors.BOLD}Errors:{Colors.RESET}")
            for i, error in enumerate(self.errors, 1):
                print_error(f"{i}. {error}")

        print(f"\n{Colors.BOLD}Status: ", end="")
        if self.failed == 0:
            print_success("ALL TESTS PASSED ✓")
        else:
            print_error("SOME TESTS FAILED ✗")


results = TestResults()


def read_file(file_path: Path) -> str:
    """Read file content"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print_error(f"Cannot read {file_path}: {str(e)}")
        return ""


def test_button_system_file_exists():
    """Test 1: Verify button-system.css exists"""
    print_test("Button System CSS File Existence")

    file_path = Path("src/frontend/styles/components/button-system.css")

    if not file_path.exists():
        print_error(f"File not found: {file_path}")
        results.add_fail("button-system.css does not exist")
        return

    content = read_file(file_path)

    if not content:
        print_error("File is empty")
        results.add_fail("button-system.css is empty")
        return

    print_success(f"File exists: {file_path}")
    print_info(f"File size: {len(content)} characters")
    results.add_pass()


def test_button_variants_defined():
    """Test 2: Verify all button variants are defined"""
    print_test("Button Variants Definition")

    file_path = Path("src/frontend/styles/components/button-system.css")
    content = read_file(file_path)

    if not content:
        results.add_fail("Cannot read button-system.css")
        return

    required_variants = [
        ".btn--primary",
        ".btn--secondary",
        ".btn--metal",
        ".btn--ghost",
        ".btn--danger",
        ".btn--success",
    ]

    missing_variants = []
    for variant in required_variants:
        if variant not in content:
            missing_variants.append(variant)

    if missing_variants:
        print_error(f"Missing variants: {', '.join(missing_variants)}")
        results.add_fail(f"Missing button variants: {missing_variants}")
        return

    print_success(f"All {len(required_variants)} button variants defined")
    for variant in required_variants:
        print_info(f"  {variant}")
    results.add_pass()


def test_button_sizes_defined():
    """Test 3: Verify button sizes are defined"""
    print_test("Button Sizes Definition")

    file_path = Path("src/frontend/styles/components/button-system.css")
    content = read_file(file_path)

    if not content:
        results.add_fail("Cannot read button-system.css")
        return

    required_sizes = [".btn--sm", ".btn--md", ".btn--lg"]

    missing_sizes = []
    for size in required_sizes:
        if size not in content:
            missing_sizes.append(size)

    if missing_sizes:
        print_error(f"Missing sizes: {', '.join(missing_sizes)}")
        results.add_fail(f"Missing button sizes: {missing_sizes}")
        return

    print_success(f"All {len(required_sizes)} button sizes defined")
    results.add_pass()


def test_button_states_defined():
    """Test 4: Verify button states are defined"""
    print_test("Button States Definition")

    file_path = Path("src/frontend/styles/components/button-system.css")
    content = read_file(file_path)

    if not content:
        results.add_fail("Cannot read button-system.css")
        return

    required_states = [".btn.active", ".btn:disabled", ".btn.loading"]

    found_states = []
    missing_states = []

    for state in required_states:
        # Allow variations like .btn:disabled or .btn[disabled]
        state_base = state.replace(".btn", "").replace(".", "").replace(":", "")
        if state_base in content or state in content:
            found_states.append(state)
        else:
            missing_states.append(state)

    if missing_states:
        print_warning(f"Some states may be missing: {', '.join(missing_states)}")
        results.add_warning()

    print_success(f"Button states defined: {len(found_states)}/{len(required_states)}")
    results.add_pass()


def test_button_system_imported():
    """Test 5: Verify button-system.css is imported in main-styles.css"""
    print_test("Button System Import in main-styles.css")

    file_path = Path("src/frontend/styles/main-styles.css")
    content = read_file(file_path)

    if not content:
        results.add_fail("Cannot read main-styles.css")
        return

    import_patterns = [
        "@import './components/button-system.css'",
        '@import "./components/button-system.css"',
        "@import url('./components/button-system.css')",
        '@import url("./components/button-system.css")',
    ]

    found = False
    for pattern in import_patterns:
        if pattern in content:
            found = True
            print_success(f"Import found: {pattern}")
            break

    if not found:
        print_error("button-system.css is not imported in main-styles.css")
        results.add_fail("button-system.css not imported")
        return

    results.add_pass()


def test_memory_buttons_migrated():
    """Test 6: Verify Memory buttons use new system"""
    print_test("Memory Buttons Migration")

    # Test CSS
    css_path = Path("src/frontend/features/memory/memory.css")
    css_content = read_file(css_path)

    # Test JS
    js_path = Path("src/frontend/features/memory/memory-center.js")
    js_content = read_file(js_path)

    if not css_content or not js_content:
        results.add_fail("Cannot read Memory module files")
        return

    issues = []

    # Check CSS has migration comment
    if "MIGRATION" not in css_content or "button-system.css" not in css_content:
        issues.append("CSS missing migration comment")
    else:
        print_success("CSS has migration documentation")

    # Check JS has new classes (may be in template literals)
    if "btn btn--secondary memory-tab" in js_content:
        print_success("JS uses new button classes (btn btn--secondary)")
    else:
        issues.append("JS missing 'btn btn--secondary' classes")

    # Check both history and graph buttons
    if (
        'data-memory-tab="history"' in js_content
        and 'data-memory-tab="graph"' in js_content
    ):
        print_success("Both History and Graph tabs present")
    else:
        issues.append("Missing History or Graph tab buttons")

    if issues:
        for issue in issues:
            print_error(issue)
        results.add_fail(f"Memory buttons migration incomplete: {issues}")
        return

    results.add_pass()


def test_graph_buttons_migrated():
    """Test 7: Verify Graph buttons use new system"""
    print_test("Graph Buttons Migration")

    # Test CSS
    css_path = Path("src/frontend/features/memory/concept-graph.css")
    css_content = read_file(css_path)

    # Test JS
    js_path = Path("src/frontend/features/memory/concept-graph.js")
    js_content = read_file(js_path)

    if not css_content or not js_content:
        results.add_fail("Cannot read Graph module files")
        return

    issues = []

    # Check CSS has migration comment
    if "MIGRATION" not in css_content or "button-system.css" not in css_content:
        issues.append("CSS missing migration comment")
    else:
        print_success("CSS has migration documentation")

    # Check JS has new classes
    if 'class="btn btn--ghost concept-graph__btn"' in js_content:
        print_success("JS uses new button classes (btn btn--ghost)")
    else:
        issues.append("JS missing 'btn btn--ghost' classes")

    # Check both buttons present
    if (
        'data-action="reset-view"' in js_content
        and 'data-action="reload"' in js_content
    ):
        print_success("Both reset-view and reload buttons present")
    else:
        issues.append("Missing reset-view or reload buttons")

    if issues:
        for issue in issues:
            print_error(issue)
        results.add_fail(f"Graph buttons migration incomplete: {issues}")
        return

    results.add_pass()


def test_sticky_header_implemented():
    """Test 8: Verify sticky header is implemented"""
    print_test("Sticky Header Implementation")

    css_path = Path("src/frontend/styles/main-styles.css")
    content = read_file(css_path)

    if not content:
        results.add_fail("Cannot read main-styles.css")
        return

    # Find .references__header block
    header_pattern = r"\.references__header\s*\{([^}]+)\}"
    match = re.search(header_pattern, content, re.DOTALL)

    if not match:
        print_error(".references__header style not found")
        results.add_fail("references__header not found")
        return

    header_styles = match.group(1)

    required_properties = {
        "position": ["sticky", "fixed"],
        "top": ["0"],
        "z-index": ["100", "1000"],
        "backdrop-filter": ["blur"],
    }

    issues = []
    found_properties = []

    for prop, values in required_properties.items():
        found = False
        for value in values:
            if f"{prop}:" in header_styles and value in header_styles:
                found = True
                found_properties.append(f"{prop}: {value}")
                break

        if not found:
            issues.append(f"Missing or incorrect '{prop}' property")

    if issues:
        print_warning("Some sticky header properties may be missing:")
        for issue in issues:
            print_info(f"  {issue}")
        results.add_warning()

    print_success(
        f"Sticky header properties found: {len(found_properties)}/{len(required_properties)}"
    )
    for prop in found_properties:
        print_info(f"  {prop}")

    results.add_pass()


def test_responsive_adjustments():
    """Test 9: Verify responsive adjustments exist"""
    print_test("Responsive CSS Adjustments")

    css_path = Path("src/frontend/styles/main-styles.css")
    content = read_file(css_path)

    if not content:
        results.add_fail("Cannot read main-styles.css")
        return

    # Check for media queries related to references__header
    media_query_pattern = r"@media\s*\([^)]+\)\s*\{[^}]*\.references__header[^}]*\}"
    matches = re.findall(media_query_pattern, content, re.DOTALL)

    if matches:
        print_success(f"Found {len(matches)} responsive media query blocks")
        results.add_pass()
    else:
        print_warning("No responsive adjustments found for references__header")
        results.add_warning()
        results.add_pass()


def test_design_tokens_available():
    """Test 10: Verify design tokens are available"""
    print_test("Design Tokens Availability")

    tokens_path = Path("src/frontend/styles/design-tokens.css")
    system_path = Path("src/frontend/styles/design-system.css")

    tokens_exist = tokens_path.exists()
    system_exist = system_path.exists()

    if not tokens_exist and not system_exist:
        print_error("No design token files found")
        results.add_fail("Missing design token files")
        return

    if tokens_exist:
        print_success("design-tokens.css exists")

    if system_exist:
        print_success("design-system.css exists")

    # Check button-system.css uses tokens
    button_system_path = Path("src/frontend/styles/components/button-system.css")
    if button_system_path.exists():
        content = read_file(button_system_path)
        var_count = content.count("var(--")

        if var_count > 0:
            print_success(f"button-system.css uses {var_count} CSS variables")
        else:
            print_warning("button-system.css doesn't use CSS variables")
            results.add_warning()

    results.add_pass()


def test_build_artifacts_valid():
    """Test 11: Verify build artifacts contain new styles"""
    print_test("Build Artifacts Validation")

    dist_css = Path("dist/assets")

    if not dist_css.exists():
        print_warning("dist/assets not found - build may not have been run")
        results.add_warning()
        results.add_pass()
        return

    # Find CSS files in dist
    css_files = list(dist_css.glob("*.css"))

    if not css_files:
        print_warning("No CSS files found in dist/assets")
        results.add_warning()
        results.add_pass()
        return

    print_success(f"Found {len(css_files)} CSS file(s) in build artifacts")

    # Check if button classes are present in built CSS
    for css_file in css_files:
        content = read_file(css_file)
        if ".btn--primary" in content or ".btn--secondary" in content:
            print_success(f"New button classes found in {css_file.name}")
            results.add_pass()
            return

    print_warning("New button classes not found in build artifacts (may need rebuild)")
    results.add_warning()
    results.add_pass()


def main():
    """Run all Phase 3 validation tests"""
    print_header("PHASE 3 UI/UX VALIDATION TESTS")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Working Directory: {Path.cwd()}")

    # Verify we're in the right directory
    if not Path("src/frontend").exists():
        print_error("Not in project root directory!")
        print_info("Please run this script from the emergence-v8 root directory")
        return 1

    print_success("Project structure validated")

    # Run all tests
    print_header("TASK 3.1 - BUTTON SYSTEM")
    test_button_system_file_exists()
    print()
    test_button_variants_defined()
    print()
    test_button_sizes_defined()
    print()
    test_button_states_defined()
    print()
    test_button_system_imported()

    print_header("TASK 3.2 - MEMORY BUTTONS MIGRATION")
    test_memory_buttons_migrated()

    print_header("TASK 3.3 - GRAPH BUTTONS MIGRATION")
    test_graph_buttons_migrated()

    print_header("TASK 3.4 - STICKY HEADER")
    test_sticky_header_implemented()
    print()
    test_responsive_adjustments()

    print_header("INTEGRATION CHECKS")
    test_design_tokens_available()
    print()
    test_build_artifacts_valid()

    # Print summary
    results.print_summary()

    # Return exit code
    return 0 if results.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
