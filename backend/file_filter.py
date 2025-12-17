"""
Smart File Filter for Knowledge AI
Handles ignore patterns, sensitive file detection, and content quality filtering.
"""

import re
import os
from pathlib import Path
from typing import Set, List, Tuple, Optional
from dataclasses import dataclass, field
from fnmatch import fnmatch


@dataclass
class FilterResult:
    """Result of filtering a file."""
    should_index: bool
    reason: Optional[str] = None
    category: Optional[str] = None  # 'ignored', 'sensitive', 'quality', 'size', etc.


@dataclass
class FilterStats:
    """Statistics about filtered files."""
    total_scanned: int = 0
    indexed: int = 0
    ignored_by_pattern: int = 0
    ignored_sensitive: int = 0
    ignored_size: int = 0
    ignored_quality: int = 0
    ignored_binary: int = 0
    
    def to_dict(self):
        return {
            "total_scanned": self.total_scanned,
            "indexed": self.indexed,
            "ignored": {
                "by_pattern": self.ignored_by_pattern,
                "sensitive": self.ignored_sensitive,
                "size": self.ignored_size,
                "quality": self.ignored_quality,
                "binary": self.ignored_binary,
            }
        }


class SmartFileFilter:
    """
    Intelligent file filtering for knowledge base indexing.
    Handles ignore patterns, sensitive files, and quality filtering.
    """
    
    # =========================================================================
    # Default Ignore Patterns (always ignored unless explicitly included)
    # =========================================================================
    
    DEFAULT_IGNORE_DIRS: Set[str] = {
        # Version control
        ".git", ".svn", ".hg", ".bzr",
        
        # Dependencies & packages
        "node_modules", "bower_components", "jspm_packages",
        "vendor", "vendors",
        "packages",
        
        # Python
        "venv", "env", ".venv", ".env",
        "virtualenv", ".virtualenv",
        "__pycache__", ".pytest_cache", ".mypy_cache",
        "*.egg-info", ".eggs", "dist", "build",
        ".tox", ".nox",
        
        # Ruby
        ".bundle", "vendor/bundle",
        
        # Java/Kotlin/Scala
        "target", ".gradle", ".mvn",
        "out", "classes",
        
        # .NET
        "bin", "obj", "packages",
        
        # iOS/macOS
        "Pods", ".cocoapods",
        "Carthage",
        
        # Build outputs
        "dist", "build", "out", "output",
        "_build", ".build",
        "release", "debug",
        
        # IDE & editors
        ".idea", ".vscode", ".vs",
        ".eclipse", ".settings",
        "*.xcworkspace", "*.xcodeproj",
        ".atom", ".sublime-*",
        
        # Caches
        ".cache", "cache", "caches",
        ".parcel-cache", ".next", ".nuxt",
        ".turbo", ".webpack",
        
        # Coverage & testing
        "coverage", ".coverage", "htmlcov",
        ".nyc_output", "__snapshots__",
        
        # Documentation builds
        "_site", "site", ".docusaurus",
        "docs/_build", "public",
        
        # Logs
        "logs", "log", "*.log",
        
        # Temporary
        "tmp", "temp", ".tmp",
        
        # OS files
        ".DS_Store", "Thumbs.db",
        
        # Terraform/Infrastructure
        ".terraform", "terraform.tfstate.d",
        
        # Docker
        ".docker",
        
        # Misc
        ".vagrant", ".serverless",
        "bower_components",
    }
    
    DEFAULT_IGNORE_FILES: Set[str] = {
        # Lock files (usually auto-generated, not useful for knowledge)
        "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
        "Pipfile.lock", "poetry.lock", "Cargo.lock",
        "Gemfile.lock", "composer.lock",
        "pubspec.lock", "packages.lock.json",
        
        # Build manifests (often duplicative or auto-generated)
        "*.min.js", "*.min.css",
        "*.bundle.js", "*.chunk.js",
        "*.map",  # Source maps
        
        # Binary & compiled
        "*.pyc", "*.pyo", "*.pyd",
        "*.so", "*.dylib", "*.dll",
        "*.class", "*.jar", "*.war",
        "*.exe", "*.bin", "*.out",
        "*.o", "*.a", "*.lib",
        "*.wasm",
        
        # Archives
        "*.zip", "*.tar", "*.gz", "*.rar", "*.7z",
        "*.tgz", "*.bz2", "*.xz",
        
        # Images (unless specifically requested)
        "*.png", "*.jpg", "*.jpeg", "*.gif", "*.webp",
        "*.ico", "*.svg", "*.bmp", "*.tiff",
        "*.psd", "*.ai", "*.sketch",
        
        # Audio/Video
        "*.mp3", "*.wav", "*.ogg", "*.flac",
        "*.mp4", "*.avi", "*.mov", "*.mkv", "*.webm",
        
        # Fonts
        "*.woff", "*.woff2", "*.ttf", "*.otf", "*.eot",
        
        # Database files
        "*.db", "*.sqlite", "*.sqlite3",
        "*.mdb", "*.accdb",
        
        # Generated documentation
        "*.pdf",  # Often auto-generated
        
        # Editor backups
        "*~", "*.swp", "*.swo", "*.bak",
        ".*.swp", ".*.swo",
        
        # Misc
        ".gitignore", ".gitattributes", ".gitmodules",
        ".dockerignore", ".npmignore",
        ".editorconfig", ".prettierignore",
        "Makefile", "CMakeLists.txt",
        "Dockerfile", "docker-compose*.yml",
        ".travis.yml", ".gitlab-ci.yml",
        "Jenkinsfile", "azure-pipelines.yml",
        ".pre-commit-config.yaml",
    }
    
    # =========================================================================
    # Sensitive File Patterns (NEVER index these)
    # =========================================================================
    
    SENSITIVE_PATTERNS: Set[str] = {
        # Environment files
        ".env", ".env.*", "*.env",
        ".env.local", ".env.development", ".env.production",
        ".env.test", ".env.staging",
        
        # Credentials & secrets
        "credentials", "credentials.*",
        "secrets", "secrets.*", "*.secret", "*.secrets",
        "*credential*", "*secret*",
        ".netrc", ".npmrc", ".pypirc",
        
        # API keys & tokens
        "*api_key*", "*apikey*",
        "*api-key*", "*token*",
        "*access_key*", "*secret_key*",
        
        # SSH & certificates
        "id_rsa", "id_rsa.*", "id_dsa", "id_ed25519",
        "*.pem", "*.key", "*.crt", "*.cer",
        "*.p12", "*.pfx", "*.jks",
        "known_hosts", "authorized_keys",
        ".ssh/*",
        
        # AWS
        "aws_credentials", ".aws/credentials",
        "*.aws", "aws-exports.js",
        
        # GCP
        "*-credentials.json", "service-account*.json",
        "gcp-*.json", "google-*.json",
        
        # Azure
        "azure*.json", ".azure/*",
        
        # Database
        "database.yml", "database.json",
        "*_database_url*",
        
        # Kubernetes secrets
        "*-secret.yaml", "*-secret.yml",
        "kubeconfig", ".kube/config",
        
        # Terraform secrets
        "*.tfvars", "terraform.tfstate*",
        
        # Ansible vault
        "*vault*.yml", "*vault*.yaml",
        
        # Password files
        "*password*", "passwd", "shadow",
        "htpasswd", ".htpasswd",
        
        # Session & auth
        "*session*", "*.session",
        "auth.json", "auth.yaml",
        
        # Private keys
        "private*.pem", "private*.key",
        "*_private_key*",
        
        # History files (may contain sensitive commands)
        ".*_history", ".bash_history", ".zsh_history",
        ".python_history", ".node_repl_history",
    }
    
    # Content patterns that indicate sensitive data
    SENSITIVE_CONTENT_PATTERNS: List[re.Pattern] = [
        re.compile(r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?[\w\-]{20,}'),
        re.compile(r'(?i)(secret[_-]?key|secretkey)\s*[=:]\s*["\']?[\w\-]{20,}'),
        re.compile(r'(?i)(access[_-]?key|accesskey)\s*[=:]\s*["\']?[\w\-]{20,}'),
        re.compile(r'(?i)(auth[_-]?token|authtoken)\s*[=:]\s*["\']?[\w\-]{20,}'),
        re.compile(r'(?i)password\s*[=:]\s*["\']?[^\s"\']{8,}'),
        re.compile(r'(?i)(aws[_-]?access[_-]?key[_-]?id)\s*[=:]\s*["\']?[A-Z0-9]{20}'),
        re.compile(r'(?i)(aws[_-]?secret[_-]?access[_-]?key)\s*[=:]\s*["\']?[\w/+=]{40}'),
        re.compile(r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----'),
        re.compile(r'-----BEGIN\s+CERTIFICATE-----'),
        re.compile(r'(?i)bearer\s+[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+'),  # JWT-like
        re.compile(r'ghp_[a-zA-Z0-9]{36}'),  # GitHub personal access token
        re.compile(r'sk-[a-zA-Z0-9]{48}'),  # OpenAI API key
        re.compile(r'sk-ant-[a-zA-Z0-9\-]{90,}'),  # Anthropic API key
    ]
    
    # =========================================================================
    # Quality Indicators (files that are likely low-value)
    # =========================================================================
    
    LOW_QUALITY_INDICATORS = {
        # Minified code detection
        "minified": [
            lambda content: len(content) > 1000 and '\n' not in content[:1000],
            lambda content: content.count(';') > len(content) / 50,  # Very high semicolon density
        ],
        
        # Auto-generated code markers
        "auto_generated": [
            "DO NOT EDIT",
            "AUTO-GENERATED",
            "AUTOGENERATED",
            "Generated by",
            "This file is generated",
            "Code generated by",
            "DO NOT MODIFY",
            "@generated",
            "// <auto-generated>",
        ],
        
        # Binary/garbage content
        "binary_content": [
            lambda content: sum(1 for c in content[:1000] if ord(c) < 32 and c not in '\n\r\t') > 50,
        ],
    }
    
    def __init__(
        self,
        custom_ignore_file: str = ".knowledgeignore",
        min_file_size: int = 50,  # bytes
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        check_sensitive_content: bool = True,
        extra_ignore_patterns: Optional[List[str]] = None,
        extra_include_patterns: Optional[List[str]] = None,
    ):
        """
        Initialize the smart file filter.
        
        Args:
            custom_ignore_file: Name of custom ignore file (like .gitignore)
            min_file_size: Minimum file size to index (skip tiny files)
            max_file_size: Maximum file size to index (skip huge files)
            check_sensitive_content: Whether to scan file contents for secrets
            extra_ignore_patterns: Additional patterns to ignore
            extra_include_patterns: Patterns to explicitly include (override ignores)
        """
        self.custom_ignore_file = custom_ignore_file
        self.min_file_size = min_file_size
        self.max_file_size = max_file_size
        self.check_sensitive_content = check_sensitive_content
        
        self.extra_ignore_patterns = set(extra_ignore_patterns or [])
        self.extra_include_patterns = set(extra_include_patterns or [])
        
        # Combined patterns
        self.ignore_dirs = self.DEFAULT_IGNORE_DIRS.copy()
        self.ignore_files = self.DEFAULT_IGNORE_FILES.copy()
        self.sensitive_patterns = self.SENSITIVE_PATTERNS.copy()
        
        # Cache for parsed .knowledgeignore files
        self._ignore_cache: dict[Path, Set[str]] = {}
    
    def load_custom_ignores(self, base_path: Path) -> Set[str]:
        """Load custom ignore patterns from .knowledgeignore file."""
        if base_path in self._ignore_cache:
            return self._ignore_cache[base_path]
        
        patterns = set()
        ignore_file = base_path / self.custom_ignore_file
        
        if ignore_file.exists():
            try:
                for line in ignore_file.read_text().splitlines():
                    line = line.strip()
                    # Skip comments and empty lines
                    if line and not line.startswith('#'):
                        patterns.add(line)
            except Exception:
                pass
        
        self._ignore_cache[base_path] = patterns
        return patterns
    
    def _matches_pattern(self, path: Path, patterns: Set[str]) -> bool:
        """Check if a path matches any of the given patterns."""
        name = path.name
        str_path = str(path)
        
        for pattern in patterns:
            # Check exact name match
            if fnmatch(name, pattern):
                return True
            # Check full path match
            if fnmatch(str_path, pattern):
                return True
            # Check if any parent directory matches
            for parent in path.parents:
                if fnmatch(parent.name, pattern):
                    return True
        
        return False
    
    def _is_in_ignored_directory(self, path: Path, base_path: Path) -> Tuple[bool, Optional[str]]:
        """Check if the file is inside an ignored directory."""
        try:
            rel_path = path.relative_to(base_path)
        except ValueError:
            rel_path = path
        
        for part in rel_path.parts[:-1]:  # Exclude the filename itself
            if part in self.ignore_dirs:
                return True, f"Inside ignored directory: {part}"
            # Check glob patterns
            for pattern in self.ignore_dirs:
                if fnmatch(part, pattern):
                    return True, f"Inside ignored directory matching: {pattern}"
        
        return False, None
    
    def _is_sensitive_file(self, path: Path) -> Tuple[bool, Optional[str]]:
        """Check if the file matches sensitive file patterns."""
        name = path.name.lower()
        
        for pattern in self.sensitive_patterns:
            if fnmatch(name, pattern.lower()):
                return True, f"Matches sensitive pattern: {pattern}"
        
        return False, None
    
    def _check_sensitive_content(self, content: str) -> Tuple[bool, Optional[str]]:
        """Scan content for sensitive data patterns."""
        # Only check first 10KB for performance
        sample = content[:10240]
        
        for pattern in self.SENSITIVE_CONTENT_PATTERNS:
            if pattern.search(sample):
                return True, "Contains potential sensitive data (API key, password, etc.)"
        
        return False, None
    
    def _check_file_size(self, path: Path) -> Tuple[bool, Optional[str]]:
        """Check if file size is within acceptable range."""
        try:
            size = path.stat().st_size
        except OSError:
            return False, "Could not read file size"
        
        if size < self.min_file_size:
            return False, f"File too small ({size} bytes)"
        
        if size > self.max_file_size:
            return False, f"File too large ({size / 1024 / 1024:.1f} MB)"
        
        return True, None
    
    def _check_quality(self, content: str, path: Path) -> Tuple[bool, Optional[str]]:
        """Check if file content is high enough quality to index."""
        # Check for minified code
        for check in self.LOW_QUALITY_INDICATORS["minified"]:
            if callable(check) and check(content):
                return False, "Appears to be minified code"
        
        # Check for auto-generated markers
        first_1k = content[:1024].upper()
        for marker in self.LOW_QUALITY_INDICATORS["auto_generated"]:
            if marker.upper() in first_1k:
                return False, f"Auto-generated file (contains '{marker}')"
        
        # Check for binary content
        for check in self.LOW_QUALITY_INDICATORS["binary_content"]:
            if callable(check) and check(content):
                return False, "Contains binary/non-text content"
        
        return True, None
    
    def should_index(
        self, 
        path: Path, 
        base_path: Optional[Path] = None,
        content: Optional[str] = None
    ) -> FilterResult:
        """
        Determine if a file should be indexed.
        
        Args:
            path: Path to the file
            base_path: Base directory (for loading custom ignores)
            content: File content (optional, for content-based filtering)
            
        Returns:
            FilterResult with decision and reason
        """
        if base_path is None:
            base_path = path.parent
        
        # Load custom ignores from base path
        custom_ignores = self.load_custom_ignores(base_path)
        
        # 1. Check explicit includes first (override everything)
        if self._matches_pattern(path, self.extra_include_patterns):
            return FilterResult(True, "Explicitly included", "included")
        
        # 2. Check if in ignored directory
        in_ignored, reason = self._is_in_ignored_directory(path, base_path)
        if in_ignored:
            return FilterResult(False, reason, "ignored")
        
        # 3. Check file name against ignore patterns
        if self._matches_pattern(path, self.ignore_files):
            return FilterResult(False, "Matches ignore pattern", "ignored")
        
        if self._matches_pattern(path, custom_ignores):
            return FilterResult(False, "Matches custom ignore pattern", "ignored")
        
        if self._matches_pattern(path, self.extra_ignore_patterns):
            return FilterResult(False, "Matches extra ignore pattern", "ignored")
        
        # 4. Check for sensitive files
        is_sensitive, reason = self._is_sensitive_file(path)
        if is_sensitive:
            return FilterResult(False, reason, "sensitive")
        
        # 5. Check file size
        size_ok, reason = self._check_file_size(path)
        if not size_ok:
            return FilterResult(False, reason, "size")
        
        # 6. Content-based checks (if content provided)
        if content is not None:
            # Check for sensitive content
            if self.check_sensitive_content:
                has_sensitive, reason = self._check_sensitive_content(content)
                if has_sensitive:
                    return FilterResult(False, reason, "sensitive")
            
            # Check content quality
            quality_ok, reason = self._check_quality(content, path)
            if not quality_ok:
                return FilterResult(False, reason, "quality")
        
        return FilterResult(True, None, None)
    
    def filter_paths(
        self,
        paths: List[Path],
        base_path: Path,
        read_content: bool = False
    ) -> Tuple[List[Path], FilterStats]:
        """
        Filter a list of paths and return those that should be indexed.
        
        Args:
            paths: List of file paths to filter
            base_path: Base directory for context
            read_content: Whether to read file content for filtering
            
        Returns:
            Tuple of (filtered_paths, statistics)
        """
        stats = FilterStats()
        filtered = []
        
        for path in paths:
            stats.total_scanned += 1
            
            # Read content if requested and file is small enough
            content = None
            if read_content:
                try:
                    size = path.stat().st_size
                    if size <= self.max_file_size:
                        content = path.read_text(errors='ignore')[:50000]  # First 50KB
                except Exception:
                    pass
            
            result = self.should_index(path, base_path, content)
            
            if result.should_index:
                filtered.append(path)
                stats.indexed += 1
            else:
                # Update stats based on category
                if result.category == "ignored":
                    stats.ignored_by_pattern += 1
                elif result.category == "sensitive":
                    stats.ignored_sensitive += 1
                elif result.category == "size":
                    stats.ignored_size += 1
                elif result.category == "quality":
                    stats.ignored_quality += 1
                elif result.category == "binary":
                    stats.ignored_binary += 1
        
        return filtered, stats
    
    def get_summary(self) -> dict:
        """Get a summary of current filter configuration."""
        return {
            "ignored_directories": len(self.ignore_dirs),
            "ignored_file_patterns": len(self.ignore_files),
            "sensitive_patterns": len(self.sensitive_patterns),
            "min_file_size": self.min_file_size,
            "max_file_size": self.max_file_size,
            "check_sensitive_content": self.check_sensitive_content,
            "custom_ignore_file": self.custom_ignore_file,
        }


# ============================================================================
# Preset Configurations
# ============================================================================

def create_code_project_filter() -> SmartFileFilter:
    """Create a filter optimized for code repositories."""
    return SmartFileFilter(
        min_file_size=10,  # Allow smaller files for code
        max_file_size=5 * 1024 * 1024,  # 5MB max
        check_sensitive_content=True,
    )


def create_notes_filter() -> SmartFileFilter:
    """Create a filter optimized for note-taking folders."""
    return SmartFileFilter(
        min_file_size=10,
        max_file_size=50 * 1024 * 1024,  # 50MB for PDFs
        check_sensitive_content=False,  # Notes usually don't have API keys
        extra_ignore_patterns={"*.exe", "*.dll", "*.so"},  # Still ignore binaries
    )


def create_research_filter() -> SmartFileFilter:
    """Create a filter optimized for research/academic content."""
    filter = SmartFileFilter(
        min_file_size=100,
        max_file_size=100 * 1024 * 1024,  # 100MB for large PDFs
        check_sensitive_content=False,
    )
    # Remove PDF from ignore list for research
    filter.ignore_files.discard("*.pdf")
    return filter
