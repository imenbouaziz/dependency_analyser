"""
class_dependency_parser.py
Analyzes internal dependencies between Java classes in the codebase.

Maps:
- Class A uses Class B
- Method calls between classes
- Field type dependencies
- Inheritance relationships
- Interface implementations
- Package coupling

Use case: Service decomposition, refactoring, finding circular dependencies
"""

from __future__ import annotations
import os
import re
from typing import Dict, List, Set, Tuple
from pathlib import Path
from collections import defaultdict


class ClassInfo:
    """Information about a Java class."""
    def __init__(self, name: str, package: str, file_path: str):
        self.name = name
        self.package = package
        self.full_name = f"{package}.{name}" if package else name
        self.file_path = file_path
        self.extends = None  # Parent class
        self.implements = []  # Interfaces
        self.fields = []  # Field types
        self.attributes = []  # Detailed attribute info: [{name, type, visibility, annotations}]
        self.dependencies = set()  # Other classes this class uses
        self.methods = []  # Method signatures
        self.attribute_access = []  # Which attributes of other classes this class accesses
        self.accessed_by = []  # Which classes access this class's attributes


def extract_class_info(file_path: str, content: str) -> List[ClassInfo]:
    """
    Extract class declarations and basic info from a Java file.
    
    Returns:
        List of ClassInfo objects (can have multiple classes per file)
    """
    classes = []
    
    # Extract package
    package_match = re.search(r'package\s+([a-zA-Z_][\w.]*)\s*;', content)
    package_name = package_match.group(1) if package_match else ""
    
    # Find all class/interface/enum declarations
    # Pattern: [public] [abstract] [final] (class|interface|enum) ClassName [extends Parent] [implements I1, I2]
    class_pattern = r'(?:public\s+)?(?:abstract\s+)?(?:final\s+)?(class|interface|enum)\s+(\w+)(?:\s+extends\s+([\w.]+))?(?:\s+implements\s+([\w\s,.<>]+))?'
    
    for match in re.finditer(class_pattern, content):
        class_type = match.group(1)
        class_name = match.group(2)
        extends = match.group(3)
        implements_str = match.group(4)
        
        cls = ClassInfo(class_name, package_name, file_path)
        
        if extends:
            cls.extends = extends
            cls.dependencies.add(extends)
        
        if implements_str:
            # Parse comma-separated interfaces
            interfaces = [i.strip() for i in re.split(r'[,\s]+', implements_str) if i.strip()]
            cls.implements = interfaces
            cls.dependencies.update(interfaces)
        
        classes.append(cls)
    
    return classes


def extract_field_dependencies(content: str, class_info: ClassInfo):
    """
    Find field declarations and their types.
    
    Example:
        private UserService userService;
        private List<Order> orders;
        @Autowired private final OrderRepository orderRepository;
    """
    # Pattern: [annotations] [visibility] [static] [final] Type fieldName
    field_pattern = r'(?:@\w+\s+)*(?:private|public|protected)\s+(?:static\s+)?(?:final\s+)?(\w+(?:<[\w\s,.<>]+>)?)\s+(\w+)\s*[;=]'
    
    for match in re.finditer(field_pattern, content):
        field_type = match.group(1)
        field_name = match.group(2)
        
        # Extract annotations for this field (look backward)
        field_start = match.start()
        preceding_text = content[max(0, field_start - 200):field_start]
        annotations = re.findall(r'@(\w+)', preceding_text)
        
        # Determine visibility
        visibility_match = re.search(r'(private|public|protected)', match.group(0))
        visibility = visibility_match.group(1) if visibility_match else "package"
        
        # Extract base type (remove generics)
        base_type = re.sub(r'<.*?>', '', field_type).strip()
        
        # Store detailed attribute info
        class_info.attributes.append({
            "name": field_name,
            "type": field_type,
            "base_type": base_type,
            "visibility": visibility,
            "annotations": annotations
        })
        
        # Skip primitive types and common Java types
        if base_type not in {'int', 'long', 'double', 'float', 'boolean', 'char', 'byte', 'short', 
                             'String', 'Integer', 'Long', 'Double', 'Float', 'Boolean', 
                             'List', 'Set', 'Map', 'Collection', 'ArrayList', 'HashMap', 'HashSet',
                             'Optional', 'Stream', 'void'}:
            class_info.fields.append(base_type)
            class_info.dependencies.add(base_type)


def extract_method_calls(content: str, class_info: ClassInfo, all_class_names: Set[str]):
    """
    Find method calls that might be to other classes in the codebase.
    
    Examples:
        userService.findById(id)
        OrderService.create(order)
        new UserRepository()
    """
    # Pattern: variable.methodName() or ClassName.methodName()
    method_call_pattern = r'(\w+)\.(\w+)\s*\('
    
    for match in re.finditer(method_call_pattern, content):
        caller = match.group(1)
        method = match.group(2)
        
        # Check if caller is a known class name (static call)
        if caller in all_class_names:
            class_info.dependencies.add(caller)
        
        # Detect getter/setter calls (attribute access)
        if method.startswith('get') or method.startswith('set') or method.startswith('is'):
            # Extract attribute name: getUserName -> userName, isActive -> active
            if method.startswith('get') or method.startswith('set'):
                attr_name = method[3:]  # Remove 'get'/'set'
            else:  # is
                attr_name = method[2:]  # Remove 'is'
            
            if attr_name:
                attr_name = attr_name[0].lower() + attr_name[1:] if len(attr_name) > 1 else attr_name.lower()
                class_info.attribute_access.append({
                    "target_class": caller,
                    "attribute": attr_name,
                    "access_type": "getter" if method.startswith('get') or method.startswith('is') else "setter",
                    "method": method
                })
    
    # Pattern: new ClassName()
    instantiation_pattern = r'new\s+(\w+)(?:<[^>]+>)?\s*\('
    
    for match in re.finditer(instantiation_pattern, content):
        class_name = match.group(1)
        if class_name in all_class_names:
            class_info.dependencies.add(class_name)
    
    # Pattern: Direct field access - object.field (not followed by parenthesis)
    field_access_pattern = r'(\w+)\.(\w+)(?!\s*\()'
    
    for match in re.finditer(field_access_pattern, content):
        obj = match.group(1)
        field = match.group(2)
        
        # Skip common patterns like System.out, this.field, super.field
        if obj not in {'this', 'super', 'System', 'Math', 'Collections', 'Arrays'}:
            # Check if first letter is lowercase (likely a variable, not a class)
            if obj and obj[0].islower() and field and field[0].islower():
                class_info.attribute_access.append({
                    "target_class": obj,
                    "attribute": field,
                    "access_type": "direct",
                    "method": None
                })


def extract_method_signatures(content: str, class_info: ClassInfo):
    """
    Extract method signatures to find parameter and return types.
    
    Example:
        public User findUser(Long id) { ... }
    """
    # Pattern: [public|private|protected] [static] ReturnType methodName(params)
    method_pattern = r'(?:public|private|protected)\s+(?:static\s+)?(\w+(?:<[\w\s,.<>]+>)?)\s+(\w+)\s*\((.*?)\)'
    
    for match in re.finditer(method_pattern, content):
        return_type = match.group(1)
        method_name = match.group(2)
        params = match.group(3)
        
        # Extract return type dependency
        base_return = re.sub(r'<.*?>', '', return_type).strip()
        if base_return not in {'void', 'int', 'long', 'double', 'float', 'boolean', 'String', 'Integer', 'Long', 'Optional'}:
            class_info.dependencies.add(base_return)
        
        # Extract parameter type dependencies
        if params:
            # Split by comma (simple approach)
            for param in params.split(','):
                # Pattern: Type name
                param_match = re.search(r'(\w+(?:<[\w\s,.<>]+>)?)\s+\w+', param.strip())
                if param_match:
                    param_type = param_match.group(1)
                    base_param = re.sub(r'<.*?>', '', param_type).strip()
                    if base_param not in {'int', 'long', 'double', 'float', 'boolean', 'String', 'Integer', 'Long'}:
                        class_info.dependencies.add(base_param)
        
        class_info.methods.append(f"{return_type} {method_name}({params})")


def analyze_class_dependencies(root_path: str) -> Dict:
    """
    Analyze all Java files in a directory and build a class dependency graph.
    
    Returns:
        {
            "classes": [
                {
                    "name": "UserService",
                    "package": "com.example.service",
                    "full_name": "com.example.service.UserService",
                    "file": "src/main/java/com/example/service/UserService.java",
                    "extends": "BaseService",
                    "implements": ["Serializable"],
                    "dependencies": ["UserRepository", "User", "EmailService"],
                    "dependency_count": 3
                },
                ...
            ],
            "edges": [
                {"from": "UserService", "to": "UserRepository", "type": "uses"},
                {"from": "UserService", "to": "BaseService", "type": "extends"},
                ...
            ],
            "packages": {
                "com.example.service": ["UserService", "OrderService"],
                ...
            },
            "stats": {
                "total_classes": 50,
                "total_dependencies": 234,
                "circular_dependencies": [...],
                "most_coupled": [...],
                "isolated_classes": [...]
            }
        }
    """
    all_classes: Dict[str, ClassInfo] = {}  # full_name -> ClassInfo
    class_name_map: Dict[str, str] = {}  # simple name -> full_name
    
    # First pass: Find all classes
    for root, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in {'.git', 'target', 'build', 'node_modules', '.idea', 'out'}]
        
        for file in files:
            if file.endswith('.java'):
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    classes = extract_class_info(file_path, content)
                    
                    for cls in classes:
                        all_classes[cls.full_name] = cls
                        class_name_map[cls.name] = cls.full_name
                
                except Exception as e:
                    continue
    
    # Get all class names for dependency detection
    all_class_names = set(class_name_map.keys())
    
    # Second pass: Analyze dependencies
    for full_name, cls in all_classes.items():
        try:
            with open(cls.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            extract_field_dependencies(content, cls)
            extract_method_calls(content, cls, all_class_names)
            extract_method_signatures(content, cls)
        
        except Exception as e:
            continue
    
    # Resolve simple names to full names
    for cls in all_classes.values():
        resolved_deps = set()
        for dep in cls.dependencies:
            # Check if it's a simple name we know about
            if dep in class_name_map:
                resolved_deps.add(class_name_map[dep])
            # Check if it's already a full name
            elif dep in all_classes:
                resolved_deps.add(dep)
            # Check if it's in the same package
            elif f"{cls.package}.{dep}" in all_classes:
                resolved_deps.add(f"{cls.package}.{dep}")
        
        cls.dependencies = resolved_deps
    
    # Build output structure
    classes_output = []
    edges = []
    packages = defaultdict(list)
    
    for full_name, cls in all_classes.items():
        classes_output.append({
            "name": cls.name,
            "package": cls.package,
            "full_name": cls.full_name,
            "file": os.path.relpath(cls.file_path, root_path),
            "extends": cls.extends,
            "implements": cls.implements,
            "attributes": cls.attributes,  # Detailed attribute info
            "attribute_count": len(cls.attributes),
            "dependencies": sorted(list(cls.dependencies)),
            "dependency_count": len(cls.dependencies),
            "methods": cls.methods[:10],  # First 10 methods
            "attribute_access": cls.attribute_access  # Which attributes this class accesses
        })
        
        packages[cls.package].append(cls.name)
        
        # Create edges
        if cls.extends and cls.extends in all_classes:
            edges.append({
                "from": cls.full_name,
                "to": cls.extends if '.' in cls.extends else f"{cls.package}.{cls.extends}",
                "type": "extends"
            })
        
        for interface in cls.implements:
            edges.append({
                "from": cls.full_name,
                "to": interface,
                "type": "implements"
            })
        
        for dep in cls.dependencies:
            if dep in all_classes:
                edges.append({
                    "from": cls.full_name,
                    "to": dep,
                    "type": "uses"
                })
    
    # Calculate statistics
    dependency_counts = {cls.full_name: len(cls.dependencies) for cls in all_classes.values()}
    most_coupled = sorted(dependency_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    isolated = [name for name, count in dependency_counts.items() if count == 0]
    
    # Detect circular dependencies (simplified)
    circular = detect_circular_dependencies(all_classes)
    
    stats = {
        "total_classes": len(all_classes),
        "total_packages": len(packages),
        "total_dependencies": len(edges),
        "most_coupled": [{"class": name, "dependency_count": count} for name, count in most_coupled],
        "isolated_classes": isolated,
        "circular_dependencies": circular[:10],  # First 10
        "average_dependencies": sum(dependency_counts.values()) / len(dependency_counts) if dependency_counts else 0
    }
    
    return {
        "classes": classes_output,
        "edges": edges,
        "packages": dict(packages),
        "stats": stats
    }


def detect_circular_dependencies(classes: Dict[str, ClassInfo]) -> List[List[str]]:
    """
    Detect circular dependency chains.
    
    Returns:
        List of cycles, e.g., [["A", "B", "A"], ["X", "Y", "Z", "X"]]
    """
    cycles = []
    
    def dfs(current: str, path: List[str], visited: Set[str]):
        if current in path:
            # Found a cycle
            cycle_start = path.index(current)
            cycle = path[cycle_start:] + [current]
            if cycle not in cycles and list(reversed(cycle)) not in cycles:
                cycles.append(cycle)
            return
        
        if current in visited or current not in classes:
            return
        
        visited.add(current)
        path.append(current)
        
        for dep in classes[current].dependencies:
            dfs(dep, path.copy(), visited)
    
    for class_name in classes.keys():
        dfs(class_name, [], set())
    
    return cycles


if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) > 1:
        result = analyze_class_dependencies(sys.argv[1])
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python class_dependency_parser.py <path_to_java_src>")
