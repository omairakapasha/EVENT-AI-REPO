"""
CodeShield — Scans code blocks in agent responses for dangerous patterns.

Research basis:
- LlamaFirewall CodeShield (Meta, 2024) — code execution safety
- OWASP Top 10: Injection Prevention
- "Security of Code Generation in LLMs" (arXiv 2025)

Purpose:
When an agent generates code blocks (SQL, Python, etc.), scan for:
- SQL injection patterns
- Dangerous function calls
- Credential exposure
- Command injection

This prevents the agent from inadvertently generating harmful code
that could be copied and executed by users.
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# ── SQL Injection Patterns ───────────────────────────────────────
SQL_INJECTION_PATTERNS = [
    # Classic SQL injection
    r"'\s*OR\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+",  # ' OR '1'='1
    r"'\s*OR\s+1\s*=\s*1",  # ' OR 1=1
    r";\s*DROP\s+TABLE",  # ; DROP TABLE
    r";\s*DELETE\s+FROM",  # ; DELETE FROM
    r"UNION\s+SELECT\s+.*\s+FROM",  # UNION SELECT
    r"'\s*;\s*--",  # '; --
    r"EXEC\s*\(",  # EXEC()
    r"xp_cmdshell",
    
    # SQL keywords in suspicious context
    r"--\s*$",  # SQL comment at end
    r"/\*.*\*/",  # SQL block comment
    
    # Dangerous SQL functions
    r"\bLOAD_FILE\s*\(",
    r"\bINTO\s+OUTFILE",
    r"\bBENCHMARK\s*\(",
    r"\bSLEEP\s*\(",
    
    # NoSQL injection
    r"\$where\s*:",
    r"\$regex\s*:",
    r"\$gt\s*:\s*\{\}",
]

# ── Dangerous Python Patterns ─────────────────────────────────────
PYTHON_DANGEROUS_PATTERNS = [
    r"eval\s*\(",
    r"exec\s*\(",
    r"__import__\s*\(",
    r"compile\s*\(",
    r"open\s*\(\s*['\"].*\.\.\/",  # Path traversal
    r"os\.system\s*\(",
    r"subprocess\.(call|run|Popen)\s*\(",
    r"pickle\.loads?\s*\(",
    r"marshal\.loads?\s*\(",
    r"input\s*\(\s*['\"].*password",  # Password prompt
]

# ── Credential/Secret Patterns ────────────────────────────────────
SECRET_PATTERNS = [
    r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]",
    r"secret[_-]?key\s*=\s*['\"][^'\"]+['\"]",
    r"password\s*=\s*['\"][^'\"]+['\"]",
    r"token\s*=\s*['\"][^'\"]+['\"]",
    r"Bearer\s+[A-Za-z0-9\-._~+/]+=*",
    r"sk-[A-Za-z0-9]{20,}",  # OpenAI-style keys
    r"AKIA[0-9A-Z]{16}",  # AWS access keys
]

# ── Compiled patterns for performance ─────────────────────────────
_COMPILED_SQL = [re.compile(p, re.I | re.M) for p in SQL_INJECTION_PATTERNS]
_COMPILED_PYTHON = [re.compile(p, re.I) for p in PYTHON_DANGEROUS_PATTERNS]
_COMPILED_SECRETS = [re.compile(p, re.I) for p in SECRET_PATTERNS]

# Code block detection
_CODE_BLOCK_RE = re.compile(r"```(\w*)\n([\s\S]*?)```", re.M)
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")


@dataclass
class CodeShieldResult:
    """Result of code safety scan."""
    safe: bool
    issues: list[dict]  # List of detected issues
    sanitized_content: str
    blocked_reason: Optional[str] = None


class CodeShield:
    """
    Scans code blocks for dangerous patterns.
    
    Usage:
        shield = CodeShield()
        result = shield.scan(response_text)
        if not result.safe:
            # Redact or block the response
    """
    
    def __init__(
        self,
        block_sql_injection: bool = True,
        block_dangerous_functions: bool = True,
        block_secrets: bool = True,
    ):
        self._block_sql = block_sql_injection
        self._block_dangerous = block_dangerous_functions
        self._block_secrets = block_secrets
    
    def scan(self, content: str) -> CodeShieldResult:
        """
        Scan content for code blocks and check for dangerous patterns.
        
        Returns:
            CodeShieldResult with safety status and any detected issues
        """
        issues = []
        sanitized = content
        
        try:
            # 1. Extract and scan code blocks
            for match in _CODE_BLOCK_RE.finditer(content):
                language = match.group(1).lower()
                code = match.group(2)
                
                # Scan based on language
                if language in ("sql", "mysql", "postgresql", "sqlite"):
                    sql_issues = self._scan_sql(code)
                    issues.extend(sql_issues)
                
                elif language in ("python", "py"):
                    py_issues = self._scan_python(code)
                    issues.extend(py_issues)
                
                # Always scan for secrets regardless of language
                secret_issues = self._scan_secrets(code)
                issues.extend(secret_issues)
            
            # 2. Scan inline code for quick patterns
            for match in _INLINE_CODE_RE.finditer(content):
                inline = match.group(1)
                if any(p.search(inline) for p in _COMPILED_SECRETS):
                    issues.append({
                        "type": "secret_in_inline_code",
                        "severity": "high",
                        "match": inline[:50],
                    })
            
            # 3. Determine if content should be blocked
            high_severity = [i for i in issues if i.get("severity") == "high"]
            blocked_reason = None
            
            if high_severity:
                blocked_reason = f"Detected {len(high_severity)} high-severity issue(s)"
                sanitized = self._sanitize_dangerous_content(content, issues)
                logger.warning(
                    "CodeShield blocked content: %s",
                    blocked_reason
                )
            
            return CodeShieldResult(
                safe=len(high_severity) == 0,
                issues=issues,
                sanitized_content=sanitized,
                blocked_reason=blocked_reason,
            )
            
        except Exception as e:
            logger.error("CodeShield scan error: %s", e)
            return CodeShieldResult(
                safe=False,
                issues=[{"type": "scan_error", "severity": "high", "details": str(e)}],
                sanitized_content="[Content blocked due to scan error]",
                blocked_reason="Scan error",
            )
    
    def _scan_sql(self, code: str) -> list[dict]:
        """Scan SQL code for injection patterns."""
        issues = []
        for i, pattern in enumerate(_COMPILED_SQL):
            match = pattern.search(code)
            if match:
                issues.append({
                    "type": "sql_injection_pattern",
                    "severity": "high",
                    "pattern_index": i,
                    "match": match.group(0)[:50],
                })
        return issues
    
    def _scan_python(self, code: str) -> list[dict]:
        """Scan Python code for dangerous functions."""
        issues = []
        for i, pattern in enumerate(_COMPILED_PYTHON):
            match = pattern.search(code)
            if match:
                issues.append({
                    "type": "dangerous_python_function",
                    "severity": "high",
                    "pattern_index": i,
                    "match": match.group(0)[:50],
                })
        return issues
    
    def _scan_secrets(self, code: str) -> list[dict]:
        """Scan for exposed secrets/credentials."""
        issues = []
        for i, pattern in enumerate(_COMPILED_SECRETS):
            match = pattern.search(code)
            if match:
                issues.append({
                    "type": "exposed_secret",
                    "severity": "high",
                    "pattern_index": i,
                    "match": "[REDACTED]",
                })
        return issues
    
    def _sanitize_dangerous_content(self, content: str, issues: list[dict]) -> str:
        """Redact dangerous patterns from content."""
        sanitized = content
        
        # Redact code blocks with issues
        for issue in issues:
            if issue.get("match"):
                try:
                    # Replace the dangerous match with [REDACTED]
                    pattern = re.escape(issue["match"])
                    sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.I)
                except Exception:
                    pass
        
        return sanitized


# Singleton instance
code_shield = CodeShield()
