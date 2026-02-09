"""
java_code_parser.py
Static analysis of Java source code to detect actual dependency usage.

This parser finds:
- Import statements (which packages/classes are actually used)
- Method calls to external libraries
- API endpoint usage
- Class instantiations
- Interface implementations

This gives you REAL runtime dependency data, not just pom.xml declarations.
"""

from __future__ import annotations
import os
import re
from typing import Dict, List, Set
from pathlib import Path


def extract_imports(java_content: str) -> List[Dict]:
    """
    Extract all import statements from Java source code.
    
    Returns:
        [{"package": "org.springframework.web", "class": "RestController", "full": "org.springframework.web.RestController"}, ...]
    """
    imports = []
    # Match: import org.springframework.web.bind.annotation.RestController;
    pattern = r'import\s+(static\s+)?([a-zA-Z_][a-zA-Z0-9_.]*)\s*;'
    
    for match in re.finditer(pattern, java_content):
        full_import = match.group(2)
        parts = full_import.rsplit('.', 1)
        
        package = parts[0] if len(parts) > 1 else ""
        class_name = parts[1] if len(parts) > 1 else full_import
        
        imports.append({
            "package": package,
            "class": class_name,
            "full": full_import,
            "is_static": match.group(1) is not None
        })
    
    return imports


def extract_annotations(java_content: str) -> List[str]:
    """
    Extract all annotations used in the code.
    
    Returns:
        ["@RestController", "@Autowired", "@RequestMapping", ...]
    """
    pattern = r'@([a-zA-Z_][a-zA-Z0-9_]*)'
    return list(set(re.findall(pattern, java_content)))


def extract_api_calls(java_content: str) -> List[Dict]:
    """
    Detect potential external API/HTTP calls.
    
    Returns:
        [{"type": "RestTemplate", "method": "getForObject", "url_pattern": "..."}, ...]
    """
    api_calls = []
    
    # Patterns for common HTTP clients
    patterns = [
        # RestTemplate
        r'(restTemplate|RestTemplate)\.(get|post|put|delete|exchange)\w*\([^)]*["\']([^"\']+)["\']',
        # HttpClient
        r'(httpClient|HttpClient)\.(get|post|put|delete|send)\([^)]*["\']([^"\']+)["\']',
        # WebClient
        r'(webClient|WebClient)\.(get|post|put|delete)\(\)\.uri\(["\']([^"\']+)["\']',
        # Feign client
        r'@(GetMapping|PostMapping|PutMapping|DeleteMapping|RequestMapping)\(["\']([^"\']+)["\']',
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, java_content):
            api_calls.append({
                "client_type": match.group(1) if len(match.groups()) > 0 else "unknown",
                "method": match.group(2) if len(match.groups()) > 1 else "unknown",
                "endpoint": match.group(3) if len(match.groups()) > 2 else match.group(2),
            })
    
    return api_calls


def extract_class_usage(java_content: str, target_classes: List[str]) -> List[Dict]:
    """
    Find usage of specific classes (instantiation, method calls).
    
    Args:
        target_classes: List of class names to search for
    
    Returns:
        [{"class": "ObjectMapper", "usage_type": "instantiation", "context": "..."}, ...]
    """
    usages = []
    
    for class_name in target_classes:
        # New instance: new ClassName()
        new_pattern = rf'new\s+{class_name}\s*\('
        for match in re.finditer(new_pattern, java_content):
            usages.append({
                "class": class_name,
                "usage_type": "instantiation",
                "pattern": "new"
            })
        
        # Static method call: ClassName.methodName()
        static_pattern = rf'{class_name}\.(\w+)\s*\('
        for match in re.finditer(static_pattern, java_content):
            usages.append({
                "class": class_name,
                "usage_type": "static_method",
                "method": match.group(1)
            })
        
        # Instance method: variable.methodName() where variable is of type ClassName
        # This is harder without full AST, but we can detect declarations
        instance_pattern = rf'{class_name}\s+(\w+)\s*='
        for match in re.finditer(instance_pattern, java_content):
            usages.append({
                "class": class_name,
                "usage_type": "declaration",
                "variable": match.group(1)
            })
    
    return usages


def analyze_java_file(file_path: str) -> Dict:
    """
    Perform static analysis on a single Java file.
    
    Returns:
        {
            "file": "path/to/File.java",
            "package": "com.example.service",
            "class_name": "UserService",
            "imports": [...],
            "annotations": [...],
            "api_calls": [...],
            "external_dependencies": {
                "springframework": [...],
                "jackson": [...],
                ...
            }
        }
    """
    if not os.path.isfile(file_path):
        return {"error": f"File not found: {file_path}"}
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        return {"error": f"Could not read file: {str(e)}"}
    
    # Extract package
    package_match = re.search(r'package\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s*;', content)
    package_name = package_match.group(1) if package_match else ""
    
    # Extract class name
    class_match = re.search(r'(public\s+)?(class|interface|enum)\s+([a-zA-Z_][a-zA-Z0-9_]*)', content)
    class_name = class_match.group(3) if class_match else Path(file_path).stem
    
    # Analyze imports
    imports = extract_imports(content)
    annotations = extract_annotations(content)
    api_calls = extract_api_calls(content)
    
    # Categorize external dependencies by library
    external_deps: Dict[str, List[str]] = {}
    
    for imp in imports:
        pkg = imp["package"]
        
        # Categorize by common libraries
        if "springframework" in pkg:
            external_deps.setdefault("springframework", []).append(imp["full"])
        elif "jackson" in pkg or "fasterxml" in pkg:
            external_deps.setdefault("jackson", []).append(imp["full"])
        elif "javax" in pkg or "jakarta" in pkg:
            external_deps.setdefault("jakarta_ee", []).append(imp["full"])
        elif "org.apache" in pkg:
            external_deps.setdefault("apache_commons", []).append(imp["full"])
        elif "com.google" in pkg:
            external_deps.setdefault("google", []).append(imp["full"])
        elif "org.slf4j" in pkg or "log4j" in pkg or "logback" in pkg:
            external_deps.setdefault("logging", []).append(imp["full"])
        elif "junit" in pkg or "mockito" in pkg or "testng" in pkg:
            external_deps.setdefault("testing", []).append(imp["full"])
        elif not pkg.startswith("java.") and not pkg.startswith("javax."):
            # Other third-party libraries
            root_package = pkg.split('.')[0] if '.' in pkg else pkg
            external_deps.setdefault(root_package, []).append(imp["full"])
    
    return {
        "file": os.path.relpath(file_path),
        "package": package_name,
        "class_name": class_name,
        "imports": imports,
        "import_count": len(imports),
        "annotations": annotations,
        "api_calls": api_calls,
        "external_dependencies": external_deps,
        "dependency_summary": {lib: len(deps) for lib, deps in external_deps.items()}
    }


def scan_java_files(root_path: str, max_files: int = 1000) -> List[Dict]:
    """
    Scan all Java files in a directory tree.
    
    Args:
        root_path: Root directory to scan
        max_files: Maximum number of files to analyze
    
    Returns:
        List of analysis results for each Java file
    """
    java_files = []
    
    for root, dirs, files in os.walk(root_path):
        # Skip common non-source directories
        dirs[:] = [d for d in dirs if d not in {'.git', 'target', 'build', 'node_modules', '.idea', 'out'}]
        
        for file in files:
            if file.endswith('.java'):
                file_path = os.path.join(root, file)
                java_files.append(file_path)
                
                if len(java_files) >= max_files:
                    break
        
        if len(java_files) >= max_files:
            break
    
    results = []
    for file_path in java_files:
        result = analyze_java_file(file_path)
        if "error" not in result:
            results.append(result)
    
    return results


def aggregate_dependency_usage(analyses: List[Dict]) -> Dict:
    """
    Aggregate dependency usage across all analyzed files.
    
    Returns:
        {
            "total_files": 150,
            "libraries": {
                "springframework": {
                    "file_count": 45,
                    "import_count": 234,
                    "classes": ["RestController", "Autowired", ...]
                },
                ...
            },
            "api_calls": [...],
            "hot_dependencies": [...]  # Most widely used
        }
    """
    library_usage: Dict[str, Dict] = {}
    all_api_calls = []
    
    for analysis in analyses:
        for lib, imports in analysis.get("external_dependencies", {}).items():
            if lib not in library_usage:
                library_usage[lib] = {
                    "file_count": 0,
                    "import_count": 0,
                    "classes": set()
                }
            
            library_usage[lib]["file_count"] += 1
            library_usage[lib]["import_count"] += len(imports)
            
            # Extract class names
            for imp in imports:
                class_name = imp.split('.')[-1]
                library_usage[lib]["classes"].add(class_name)
        
        all_api_calls.extend(analysis.get("api_calls", []))
    
    # Convert sets to lists for JSON serialization
    for lib in library_usage:
        library_usage[lib]["classes"] = sorted(list(library_usage[lib]["classes"]))
    
    # Sort by usage
    hot_deps = sorted(
        [{"library": lib, **stats} for lib, stats in library_usage.items()],
        key=lambda x: x["file_count"],
        reverse=True
    )
    
    return {
        "total_files": len(analyses),
        "libraries": library_usage,
        "api_calls": all_api_calls,
        "api_call_count": len(all_api_calls),
        "hot_dependencies": hot_deps[:20]  # Top 20 most used
    }


if __name__ == "__main__":
    # Test on a Java file
    import sys
    if len(sys.argv) > 1:
        result = analyze_java_file(sys.argv[1])
        import json
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python java_code_parser.py <path_to_java_file>")
