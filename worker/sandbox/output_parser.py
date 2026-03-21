import re
from typing import Dict, List, Any

def parse_pytest_output(output: str) -> Dict[str, Any]:
    """
    Parses raw pytest output into a structured dictionary.
    Extracts passed/failed counts, failed test names, and error summaries.
    """
    summary = {
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "failures": []
    }
    
    # Extract overall counts from the last line (e.g., "1 failed, 2 passed in 0.05s")
    count_match = re.search(r"==+ (.*?) in \d+\.\d+s ==+", output)
    if count_match:
        counts_str = count_match.group(1)
        for part in counts_str.split(","):
            part = part.strip()
            if "passed" in part:
                 try: summary["passed"] = int(part.split()[0])
                 except: pass
            elif "failed" in part:
                 try: summary["failed"] = int(part.split()[0])
                 except: pass
            elif "error" in part:
                 try: summary["errors"] = int(part.split()[0])
                 except: pass
            elif "skipped" in part:
                 try: summary["skipped"] = int(part.split()[0])
                 except: pass

    # Extract failure details
    # We look for "____ [TEST_NAME] ____" and then the error message prefix "E "
    failure_matches = re.finditer(r"_+ (.*?) _+\n.*?\nE +(.*?)(?=\n\n|\n_|\n==|$)", output, re.DOTALL)
    for match in failure_matches:
        test_name = match.group(1).strip()
        error_msg = match.group(2).strip()
        summary["failures"].append({
            "test_name": test_name,
            "error_message": error_msg
        })

    return summary

def parse_npm_test_output(output: str) -> Dict[str, Any]:
    """
    Parses raw npm test/jest output into a structured dictionary.
    """
    summary = {
        "passed": 0,
        "failed": 0,
        "failures": []
    }
    
    # Jest style: "Tests:       1 failed, 2 passed, 3 total"
    count_match = re.search(r"Tests:\s+(.*)", output)
    if count_match:
        counts_str = count_match.group(1)
        for part in counts_str.split(","):
            part = part.strip()
            if "passed" in part:
                try: summary["passed"] = int(part.split()[0])
                except: pass
            elif "failed" in part:
                try: summary["failed"] = int(part.split()[0])
                except: pass

    # Jest failure detail: "● [TEST_NAME] › [ERROR_SUMMARY]"
    failure_matches = re.finditer(r"● (.*?) › (.*?)\n", output)
    for match in failure_matches:
        summary["failures"].append({
            "test_name": match.group(1).strip(),
            "error_message": match.group(2).strip()
        })
        
    return summary
