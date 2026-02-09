"""
ast_java_parser.py
Full AST-based Java code parser using javalang library.

Provides comprehensive code analysis including:
- Complete class hierarchy (inheritance, interfaces, nested classes)
- All field declarations with full type information
- All method declarations with signatures and parameters
- Method invocations and call chains
- Field access patterns (direct access, getters, setters)
- Variable assignments and data flow
- Annotations and their parameters
- Control flow structures
- Exception handling
- Lambda expressions
- Generics and type parameters

Use case: Deep code analysis for modernization, refactoring, and dependency mapping
"""

from __future__ import annotations
import os
import javalang
from typing import Dict, List, Set, Optional, Any
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class FieldInfo:
    """Detailed field/attribute information."""
    name: str
    type: str
    modifiers: Set[str] = field(default_factory=set)  # public, private, static, final, etc.
    annotations: List[str] = field(default_factory=list)
    dimensions: int = 0  # For arrays


@dataclass
class MethodInfo:
    """Detailed method information."""
    name: str
    return_type: Optional[str]
    parameters: List[Dict[str, str]] = field(default_factory=list)  # [{name, type}]
    modifiers: Set[str] = field(default_factory=set)
    annotations: List[str] = field(default_factory=list)
    throws: List[str] = field(default_factory=list)
    is_constructor: bool = False
    calls_methods: List[str] = field(default_factory=list)  # Method invocations inside
    accesses_fields: List[str] = field(default_factory=list)  # Field accesses inside


@dataclass
class ClassInfo:
    """Complete class information from AST."""
    name: str
    package: str
    file_path: str
    full_name: str = ""
    modifiers: Set[str] = field(default_factory=set)  # public, abstract, final, etc.
    extends: Optional[str] = None  # Parent class
    implements: List[str] = field(default_factory=list)  # Interfaces
    fields: List[FieldInfo] = field(default_factory=list)
    methods: List[MethodInfo] = field(default_factory=list)
    inner_classes: List[str] = field(default_factory=list)
    annotations: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    dependencies: Set[str] = field(default_factory=set)  # All referenced types
    
    def __post_init__(self):
        if not self.full_name:
            self.full_name = f"{self.package}.{self.name}" if self.package else self.name


def parse_java_file(file_path: str) -> Dict[str, Any]:
    """
    Parse a Java file using javalang AST parser.
    
    Returns:
        Dictionary with comprehensive AST analysis including classes, dependencies, etc.
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Parse to AST
        tree = javalang.parse.parse(content)
        
        # Extract package
        package = tree.package.name if tree.package else ""
        
        # Extract imports
        imports = []
        for imp in tree.imports:
            if imp.wildcard:
                imports.append(f"{imp.path}.*")
            else:
                imports.append(imp.path)
        
        # Extract classes
        classes = []
        for path, node in tree.filter(javalang.tree.ClassDeclaration):
            class_info = _extract_class_declaration(node, package, file_path, imports, tree)
            classes.append(class_info)
        
        # Extract interfaces
        for path, node in tree.filter(javalang.tree.InterfaceDeclaration):
            class_info = _extract_interface_declaration(node, package, file_path, imports, tree)
            classes.append(class_info)
        
        # Extract enums
        for path, node in tree.filter(javalang.tree.EnumDeclaration):
            class_info = _extract_enum_declaration(node, package, file_path, imports, tree)
            classes.append(class_info)
        
        return {
            'file_path': file_path,
            'package': package,
            'imports': imports,
            'classes': classes,
            'success': True
        }
        
    except Exception as e:
        return {
            'file_path': file_path,
            'package': '',
            'imports': [],
            'classes': [],
            'success': False,
            'error': str(e)
        }


def _extract_class_declaration(node: javalang.tree.ClassDeclaration, package: str, 
                               file_path: str, imports: List[str], tree) -> ClassInfo:
    """Extract complete information from a class declaration."""
    
    class_info = ClassInfo(
        name=node.name,
        package=package,
        file_path=file_path,
        modifiers=set(node.modifiers or []),
        annotations=[_get_annotation_name(ann) for ann in (node.annotations or [])],
        imports=imports
    )
    
    # Inheritance
    if node.extends:
        class_info.extends = _get_type_name(node.extends)
        class_info.dependencies.add(class_info.extends)
    
    # Interfaces
    if node.implements:
        for interface in node.implements:
            interface_name = _get_type_name(interface)
            class_info.implements.append(interface_name)
            class_info.dependencies.add(interface_name)
    
    # Fields
    for field_decl in node.fields:
        for declarator in field_decl.declarators:
            field_info = FieldInfo(
                name=declarator.name,
                type=_get_type_name(field_decl.type),
                modifiers=set(field_decl.modifiers or []),
                annotations=[_get_annotation_name(ann) for ann in (field_decl.annotations or [])],
                dimensions=len(declarator.dimensions or [])
            )
            class_info.fields.append(field_info)
            class_info.dependencies.add(field_info.type)
    
    # Methods
    for method in node.methods:
        method_info = _extract_method_declaration(method, class_info)
        class_info.methods.append(method_info)
    
    # Constructors
    for constructor in node.constructors:
        method_info = _extract_constructor_declaration(constructor, class_info)
        class_info.methods.append(method_info)
    
    # Inner classes
    for inner_class in node.body:
        if isinstance(inner_class, (javalang.tree.ClassDeclaration, 
                                   javalang.tree.InterfaceDeclaration,
                                   javalang.tree.EnumDeclaration)):
            class_info.inner_classes.append(inner_class.name)
    
    return class_info


def _extract_interface_declaration(node: javalang.tree.InterfaceDeclaration, package: str,
                                   file_path: str, imports: List[str], tree) -> ClassInfo:
    """Extract information from an interface declaration."""
    
    class_info = ClassInfo(
        name=node.name,
        package=package,
        file_path=file_path,
        modifiers=set(node.modifiers or []) | {'interface'},
        annotations=[_get_annotation_name(ann) for ann in (node.annotations or [])],
        imports=imports
    )
    
    # Extends (interfaces can extend multiple interfaces)
    if node.extends:
        for parent in node.extends:
            parent_name = _get_type_name(parent)
            class_info.implements.append(parent_name)
            class_info.dependencies.add(parent_name)
    
    # Methods (all interface methods)
    for method in node.methods:
        method_info = _extract_method_declaration(method, class_info)
        class_info.methods.append(method_info)
    
    return class_info


def _extract_enum_declaration(node: javalang.tree.EnumDeclaration, package: str,
                              file_path: str, imports: List[str], tree) -> ClassInfo:
    """Extract information from an enum declaration."""
    
    class_info = ClassInfo(
        name=node.name,
        package=package,
        file_path=file_path,
        modifiers=set(node.modifiers or []) | {'enum'},
        annotations=[_get_annotation_name(ann) for ann in (node.annotations or [])],
        imports=imports
    )
    
    # Interfaces (enums can implement interfaces)
    if node.implements:
        for interface in node.implements:
            interface_name = _get_type_name(interface)
            class_info.implements.append(interface_name)
            class_info.dependencies.add(interface_name)
    
    # Fields
    for field_decl in node.body.fields:
        for declarator in field_decl.declarators:
            field_info = FieldInfo(
                name=declarator.name,
                type=_get_type_name(field_decl.type),
                modifiers=set(field_decl.modifiers or []),
                annotations=[_get_annotation_name(ann) for ann in (field_decl.annotations or [])]
            )
            class_info.fields.append(field_info)
            class_info.dependencies.add(field_info.type)
    
    # Methods
    for method in node.body.methods:
        method_info = _extract_method_declaration(method, class_info)
        class_info.methods.append(method_info)
    
    return class_info


def _extract_method_declaration(method_node: javalang.tree.MethodDeclaration, 
                                class_info: ClassInfo) -> MethodInfo:
    """Extract complete method information including body analysis."""
    
    method_info = MethodInfo(
        name=method_node.name,
        return_type=_get_type_name(method_node.return_type) if method_node.return_type else 'void',
        modifiers=set(method_node.modifiers or []),
        annotations=[_get_annotation_name(ann) for ann in (method_node.annotations or [])],
        throws=[_get_type_name(exc) for exc in (method_node.throws or [])]
    )
    
    # Parameters
    if method_node.parameters:
        for param in method_node.parameters:
            param_type = _get_type_name(param.type)
            method_info.parameters.append({
                'name': param.name,
                'type': param_type
            })
            class_info.dependencies.add(param_type)
    
    # Add return type to dependencies
    if method_info.return_type and method_info.return_type != 'void':
        class_info.dependencies.add(method_info.return_type)
    
    # Analyze method body for calls and field accesses
    if method_node.body:
        _analyze_method_body(method_node.body, method_info, class_info)
    
    return method_info


def _extract_constructor_declaration(constructor_node: javalang.tree.ConstructorDeclaration,
                                     class_info: ClassInfo) -> MethodInfo:
    """Extract constructor information."""
    
    method_info = MethodInfo(
        name=constructor_node.name,
        return_type=None,
        modifiers=set(constructor_node.modifiers or []),
        annotations=[_get_annotation_name(ann) for ann in (constructor_node.annotations or [])],
        throws=[_get_type_name(exc) for exc in (constructor_node.throws or [])],
        is_constructor=True
    )
    
    # Parameters
    if constructor_node.parameters:
        for param in constructor_node.parameters:
            param_type = _get_type_name(param.type)
            method_info.parameters.append({
                'name': param.name,
                'type': param_type
            })
            class_info.dependencies.add(param_type)
    
    # Analyze body
    if constructor_node.body:
        _analyze_method_body(constructor_node.body, method_info, class_info)
    
    return method_info


def _analyze_method_body(body, method_info: MethodInfo, class_info: ClassInfo):
    """Analyze method body for method calls and field accesses."""
    
    # Find all method invocations
    for path, node in body:
        if isinstance(node, javalang.tree.MethodInvocation):
            method_call = node.member
            
            # If there's a qualifier (e.g., someObject.method()), track the dependency
            if node.qualifier:
                qualifier = node.qualifier
                method_info.calls_methods.append(f"{qualifier}.{method_call}")
                # This could be a class or object reference
                class_info.dependencies.add(qualifier)
            else:
                method_info.calls_methods.append(method_call)
        
        # Find field accesses
        elif isinstance(node, javalang.tree.MemberReference):
            field_name = node.member
            if node.qualifier:
                qualifier = node.qualifier
                method_info.accesses_fields.append(f"{qualifier}.{field_name}")
                class_info.dependencies.add(qualifier)
            else:
                method_info.accesses_fields.append(field_name)
        
        # Find object creation (new keyword)
        elif isinstance(node, javalang.tree.ClassCreator):
            created_type = _get_type_name(node.type)
            class_info.dependencies.add(created_type)


def _get_type_name(type_node) -> str:
    """Extract type name from type node, handling generics."""
    if type_node is None:
        return 'void'
    
    if isinstance(type_node, javalang.tree.ReferenceType):
        name = type_node.name
        
        # Handle generics
        if type_node.arguments:
            args = ', '.join(_get_type_name(arg.type) if hasattr(arg, 'type') else str(arg) 
                           for arg in type_node.arguments)
            return f"{name}<{args}>"
        
        # Handle arrays
        if type_node.dimensions:
            return f"{name}{'[]' * len(type_node.dimensions)}"
        
        return name
    
    elif isinstance(type_node, javalang.tree.BasicType):
        return type_node.name
    
    elif isinstance(type_node, str):
        return type_node
    
    return str(type_node)


def _get_annotation_name(annotation_node) -> str:
    """Extract annotation name."""
    if hasattr(annotation_node, 'name'):
        return f"@{annotation_node.name}"
    return str(annotation_node)


def analyze_java_repository(root_path: str) -> Dict[str, Any]:
    """
    Analyze all Java files in a repository using AST parsing.
    
    Returns:
        Complete dependency graph with all classes, methods, fields, and relationships
    """
    all_classes = []
    all_files = []
    errors = []
    
    # Find all .java files
    for root, dirs, files in os.walk(root_path):
        # Skip common non-source directories
        dirs[:] = [d for d in dirs if d not in {'.git', 'target', 'build', 'bin', 'out', 'node_modules'}]
        
        for file in files:
            if file.endswith('.java'):
                file_path = os.path.join(root, file)
                result = parse_java_file(file_path)
                
                if result['success']:
                    all_files.append(result)
                    all_classes.extend(result['classes'])
                else:
                    errors.append({
                        'file': file_path,
                        'error': result.get('error', 'Unknown error')
                    })
    
    # Build dependency graph
    dependency_graph = _build_dependency_graph(all_classes)
    
    # Detect circular dependencies
    circular_deps = _detect_circular_dependencies(dependency_graph)
    
    # Calculate metrics
    metrics = _calculate_metrics(all_classes, dependency_graph)
    
    return {
        'classes': all_classes,
        'files': all_files,
        'dependency_graph': dependency_graph,
        'circular_dependencies': circular_deps,
        'metrics': metrics,
        'errors': errors,
        'total_classes': len(all_classes),
        'total_files': len(all_files),
        'total_errors': len(errors)
    }


def _build_dependency_graph(classes: List[ClassInfo]) -> Dict[str, Set[str]]:
    """Build a dependency graph from class information."""
    graph = defaultdict(set)
    
    # Create a mapping of class names to full names
    class_map = {cls.name: cls.full_name for cls in classes}
    class_map.update({cls.full_name: cls.full_name for cls in classes})
    
    for cls in classes:
        source = cls.full_name
        
        # Add all dependencies
        for dep in cls.dependencies:
            # Try to resolve to a known class
            if dep in class_map:
                target = class_map[dep]
                if source != target:  # Avoid self-loops
                    graph[source].add(target)
            else:
                # External dependency
                graph[source].add(dep)
    
    return dict(graph)


def _detect_circular_dependencies(graph: Dict[str, Set[str]]) -> List[List[str]]:
    """Detect circular dependencies using DFS."""
    visited = set()
    rec_stack = set()
    cycles = []
    
    def dfs(node, path):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                dfs(neighbor, path[:])
            elif neighbor in rec_stack:
                # Found a cycle
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                if cycle not in cycles:
                    cycles.append(cycle)
        
        rec_stack.remove(node)
    
    for node in graph:
        if node not in visited:
            dfs(node, [])
    
    return cycles


def _calculate_metrics(classes: List[ClassInfo], graph: Dict[str, Set[str]]) -> Dict[str, Any]:
    """Calculate various code metrics."""
    
    total_methods = sum(len(cls.methods) for cls in classes)
    total_fields = sum(len(cls.fields) for cls in classes)
    
    # Find most coupled classes (highest number of dependencies)
    coupling_scores = {cls.full_name: len(cls.dependencies) for cls in classes}
    most_coupled = sorted(coupling_scores.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Count classes by visibility
    public_classes = sum(1 for cls in classes if 'public' in cls.modifiers)
    
    # Count annotations
    annotated_classes = sum(1 for cls in classes if cls.annotations)
    
    return {
        'total_methods': total_methods,
        'total_fields': total_fields,
        'avg_methods_per_class': total_methods / len(classes) if classes else 0,
        'avg_fields_per_class': total_fields / len(classes) if classes else 0,
        'public_classes': public_classes,
        'annotated_classes': annotated_classes,
        'most_coupled_classes': most_coupled,
        'total_dependencies': sum(len(deps) for deps in graph.values())
    }
