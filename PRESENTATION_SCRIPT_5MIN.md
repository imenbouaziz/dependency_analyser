# Dependency Analyzer Tool - Interface Demo Script (5 min)

## DEMO FLOW

### 1. HOME SCREEN (30 sec)
```
Show: App launches with welcome screen
Say: "Enter your repository path - local folder or GitHub URL"
Action: Paste path to sample_java_project
Action: Click "Analyze Repository"
```

---

### 2. LOADING → PROJECT ANALYZED (20 sec)
```
Show: Scanning progress, then results loaded
Show: Sidebar with project info
- Project Name: sample_java_project
- Ecosystem: Maven
- Nodes: 9
- Edges: 15+
```

---

### 3. TAB 1: OVERVIEW (1 min)
```
Show: Statistics boxes
- Project name
- Ecosystem type
- Total dependencies count
- Total relationships count

Show: Dependencies table
- List of artifacts with types
- Scroll through to show all

Action: Click "Generate SBOM" button
Show: SBOM generated
Action: Click "Download SBOM (JSON)"
```

---

### 4. TAB 2: CLASS DEPENDENCIES (2 min 30 sec)
```
Show: Code metrics
- Total Classes: 9
- Total Methods: 25+
- Coupling metrics displayed
Say: "Code metrics give you the full picture of complexity"

Show: "Data Coupling Analysis"
- Classes Using Getters (good encapsulation)
- Direct Field Access (bad - encapsulation violations)
Say: "10+ direct field accesses mean classes are breaking each other's encapsulation"

Show: "Most Coupled Classes"
- GodClass: 8 dependencies [HIGH coupling]
- OrderService: 5 dependencies [MEDIUM coupling]
- UserRepository: 3 dependencies [LOW coupling]
Say: "Start refactoring with HIGH coupling classes - they're your pain points"

Scroll down to show: "Circular Dependencies"
Show: Circular cycles detected
- Cycle 1: User → GodClass → User
- Cycle 2: Order → OrderService → Order
Say: "Circular dependencies create infinite loops - these must be broken"

Show: "Package Coupling"
- Bar chart showing classes per package
Say: "All 9 classes in one package - no separation of concerns"

Show: "Class Dependency Explorer"
Action: Click on a class (e.g., GodClass)
Show: Class details
- Package, file location
- Extends/Implements info
- Attributes (mark visibility: public/private/protected)
- Methods count
- Dependencies list
Say: "Dive into any class to see its structure, fields, and what it depends on"

Show: "Attribute Access Patterns"
- Getter calls (accessing through methods - good)
- Setter calls (modifying through methods - good)
- Direct Field Access (accessing fields directly - BAD)
Say: "Direct field access shows which classes are violating encapsulation"

Show: "Service Decomposition Suggestions"
- List of isolated classes (minimal dependencies)
Say: "These isolated classes are candidates for microservices extraction"
```

---

### 5. TAB 3: RUNTIME ANALYSIS (1 min)
```
Show: Summary stats
- Total files analyzed
- External libraries detected count
- API calls found count

Show: "Most Used Dependencies"
- commons-lang3: Used in 5 files
- Spring Core: Used in 4 files
- Gson: Used in 3 files

Show: Library usage details
- Bar chart of library usage
- Table with file counts

Show: "Migration Impact Preview"
- Select commons-lang3 from dropdown
- Show: "5 files would need refactoring"
- Show: "8 import statements would break"
- Show: Classes that would be affected
```

---

### 6. TAB 4: GRAPH VIEW (1 min)
```
Show: Interactive dependency graph
- Blue squares = Modules
- Orange circles = Artifacts
- Lines = Dependencies

Action: Zoom in/out on graph
Action: Pan the graph
Action: Show circular dependency loops clearly visible

Show: Display Options
- Toggle "Show Modules" checkbox
- Toggle "Show Artifacts" checkbox
- Change layout (hierarchical → force → circular)

Scroll down to show: "Export to Neo4j"
Click: "Generate Neo4j Cypher Script"
Show: Script generated success message
Action: Click "Download .cypher"

Show: "How to Import into Neo4j" section
- Show Neo4j Desktop instructions
- Show example Cypher queries
```

---

### 7. TAB 5: IMPACT ANALYSIS (1 min)
```
Show: "Artifact Coordinate" input field
Type: "org.apache.commons:commons-lang3:3.12.0"
Click: "Analyze Impact" button

Show: Agent analyzing...
Show: Results
- Which modules depend on it
- Dependency count
- Files affected
```

---

## TECHNICAL NOTES FOR DEMO

### Project to Use:
- Path: `c:\Users\ibouaziz\OneDrive - Capgemini\Bureau\sample_java_project`

### Key Highlights:
- ✓ GodClass at HIGH coupling (8 dependencies)
- ✓ Circular dependencies clearly visible
- ✓ Multiple JSON libraries (Gson + Jackson) = potential conflict
- ✓ Spring Framework dependencies (3 modules)
- ✓ Unused junit dependency visible

### Timing Per Tab:
1. Overview: 60 sec (quick scan, show SBOM download)
2. Class Dependencies: 150 sec (metrics, coupling, circular, encapsulation, class explorer, microservices)
3. Runtime Analysis: 45 sec (library usage, migration impact)
4. Graph View: 45 sec (zoom/pan, Neo4j export)
5. Impact Analysis: 35 sec (artifact search, results)

### Total: ~6 minutes of pure interface demo

---

## RECORDING TIPS

- **Cursor:** Make cursor visible/large for screen recording
- **Computer:** Use 1920x1080 resolution for clarity
- **Colors:** Ensure high contrast for video visibility
- **Speed:** Click slightly slower so changes are visible
- **Audio:** Narrate what you're doing live (no voiceover needed if live demo)
- **Pause:** 2-3 second pause on each important screen before clicking next

---

## LIVE DEMO BACKUP

If something fails during live demo:
1. Have screenshots of each tab pre-captured
2. Have pre-generated SBOM file ready to show
3. Have Neo4j Cypher script pre-generated
4. Know keyboard shortcuts (refresh page, etc.)

---

## WHAT TO SAY WHILE DEMO-ING

### Overview Tab:
"Here we see the project statistics. 9 total classes, 15 dependencies. And we can instantly generate an SBOM for compliance."

### Class Dependencies Tab:
**Code Metrics:**
"First, the metrics: 9 classes, 25+ methods. This gives you the complexity baseline."

**Data Coupling:**
"Now data coupling - this is critical. Direct field access means classes are violating each other's encapsulation. 10+ violations here. That's bad."

**Coupling Analysis:**
"Notice GodClass is flagged as HIGH coupling with 8 dependencies. These are your refactoring priorities. OrderService is MEDIUM, UserRepository is LOW. Fix high-coupling classes first."

**Circular Dependencies:**
"And critically - circular dependencies. User depends on GodClass, which depends back on User. This creates maintenance nightmares. Same with Order and OrderService. These must be broken."

**Package Separation:**
"All 9 classes in one package. Good architecture would separate this into services, repositories, models, and utilities."

**Class Details:**
"Click any class to see its full structure - what it extends, what it implements, all its fields, all its methods, and which other classes it depends on."

**Attribute Access Patterns:**
"Here's the encapsulation analysis. Getter and setter calls show good encapsulation. But direct field access - that's a violation. These classes are reaching into each other's internals."

**Microservices Suggestions:**
"Finally, the tool suggests which isolated classes can be extracted into standalone services. These ones have minimal dependencies - easy to extract."

### Runtime Analysis Tab:
"This tells us which libraries are actually used in code. See commons-lang3 is used in 5 files. If we were to remove it, all 5 would break."

### Graph View Tab:
"Here's the visual dependency map. Nodes are modules and artifacts, edges show dependencies. The circular loops are our problematic cycles. And we can export this entire graph to Neo4j for deeper analysis."

### Impact Analysis Tab:
"The most powerful feature: I search for a library, and instantly see which modules depend on it. This removes guesswork from upgrades and refactoring."
