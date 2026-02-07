"""
Improved prompt templates for Cognix
Provides consistent, high-quality prompts for various AI operations
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class PromptTemplate:
    """Template for AI prompts with metadata"""
    name: str
    template: str
    description: str
    required_variables: List[str]
    optional_variables: List[str] = None
    max_context_length: int = 8000
    system_prompt: str = None


class PromptTemplateManager:
    """Manages prompt templates for consistent AI interactions"""
    
    def __init__(self):
        self.templates = self._load_default_templates()
    
    def _load_default_templates(self) -> Dict[str, PromptTemplate]:
        """Load default prompt templates"""
        return {
            # ==========================================
            # 既存テンプレート（変更なし）
            # ==========================================
            
            "code_fix": PromptTemplate(
                name="code_fix",
                template="""Analyze and fix the following {content_type}:

    {context_info}

    Original code:
    ```{language}
    {code_content}
    ```

    Please fix any issues including:
    - Syntax errors and typos
    - Logic errors and bugs
    - Code style improvements (PEP 8 for Python, etc.)
    - Performance optimizations
    - Security vulnerabilities
    - Best practices violations

    CRITICAL: Attribute and Import Errors
    - If you see AttributeError like "type object 'Config' has no attribute 'X'"
      * Check if X is defined as a class attribute in Config
      * If X is only a module variable, either:
        Option A: Add it as a class attribute: X = X
        Option B: Import it directly: from module import X
    - Verify all imported attributes actually exist in their source files
    - Ensure consistent access patterns (instance.attr requires class attribute)

    Requirements:
    - Return ONLY the corrected code without explanations
    - Preserve the original structure and functionality
    - Use proper formatting and indentation
    - Add comments only where necessary for clarity

    Fixed code:""",
                description="Fix code issues and improve quality",
                required_variables=["content_type", "context_info", "code_content"],
                optional_variables=["language"],
                system_prompt="You are an expert code reviewer and bug fixer. Your task is to identify and fix issues in code while preserving functionality and improving quality."
            ),
            
            "code_edit": PromptTemplate(
                name="code_edit",
                template="""Help me modify the following {content_type} based on the user's request:

    {context_info}

    User request: {user_request}

    Current code:
    ```{language}
    {code_content}
    ```

    Please provide a modified version that:
    - Addresses the user's specific request
    - Maintains code quality and best practices
    - Preserves existing functionality unless explicitly asked to change it
    - Includes clear comments for significant changes

    Return only the modified code without explanations:""",
                description="Edit code based on user requests",
                required_variables=["content_type", "context_info", "user_request", "code_content"],
                optional_variables=["language"],
                system_prompt="You are an expert developer helping to modify code according to user requirements while maintaining quality and best practices."
            ),
            
            "code_generation": PromptTemplate(
                name="code_generation",
                template="""Generate implementation code based on the following specifications:

    **Goal**: {goal}

    **Analysis**:
    {analysis}

    **Implementation Plan**:
    {plan}

    {additional_context}

    Please generate production-ready code that:

    ## 1. Implementation Requirements
    - Follows the specified plan and architecture
    - Implements proper error handling and validation
    - Includes appropriate logging and debugging support
    - Follows language-specific best practices and conventions

    ## 2. Code Quality Standards
    - Clear, readable, and maintainable code
    - Comprehensive documentation and comments
    - Proper type hints and interfaces (where applicable)
    - Consistent formatting and style

    ## 3. Functionality
    - Core features as specified in the requirements
    - Edge case handling and input validation
    - Performance optimization where appropriate
    - Security considerations and safe practices

    ## 4. Structure and Organization
    - Logical code organization and modularization
    - Clear separation of concerns
    - Reusable components and utilities
    - Proper dependency management

    ## 5. Cross-File Consistency and Reference Integrity (CRITICAL)

    ### Configuration File Patterns (Python)
    When creating config.py or similar configuration files:
    - If you define a variable at module level (e.g., DATABASE_PATH = "..."), you MUST also define it as a class attribute if it will be accessed via class instances
    - Example of CORRECT pattern:
      ```python
      # Module level
      DATABASE_PATH = os.path.join(BASE_DIR, 'db.sqlite')
      
      class Config:
          # Class attribute (REQUIRED for instance access)
          DATABASE_PATH = DATABASE_PATH
          DATABASE_URI = f"sqlite:///{DATABASE_PATH}"
      ```
    - Example of INCORRECT pattern that causes AttributeError:
      ```python
      # Module level
      DATABASE_PATH = os.path.join(BASE_DIR, 'db.sqlite')
      
      class Config:
          # DATABASE_PATH is NOT defined as class attribute ❌
          DATABASE_URI = f"sqlite:///{DATABASE_PATH}"  # This works
      
      # In another file:
      config = get_config()  # Returns Config instance
      config.DATABASE_PATH  # ❌ AttributeError!
      ```

    ### Import and Attribute Access Verification
    Before using any attribute from an imported module:
    - VERIFY that the attribute actually exists in the target module
    - If importing from config.py, check what attributes are defined as class attributes vs module variables
    - Use consistent access patterns throughout the codebase

    ### Cross-File Reference Checklist
    Before generating any file that imports from another file:
    1. Review the imported module's structure (class vs module level definitions)
    2. Ensure all accessed attributes are actually defined in the target
    3. Use the same access pattern consistently (e.g., if using config.DATABASE_PATH, ensure DATABASE_PATH is a class attribute)
    4. For configuration values, prefer class attributes over module variables for better testability and consistency

    Please provide complete, working code with clear file structure indicators.""",
                description="Generate implementation code from plans",
                required_variables=["goal", "analysis", "plan"],
                optional_variables=["additional_context"],
                system_prompt="You are an expert software developer creating production-ready implementations. Generate complete, high-quality code that follows best practices and meets all specified requirements."
            ),
            
            "context_summary": PromptTemplate(
                name="context_summary",
                template="""Summarize the following code context for AI analysis:

    **Project**: {project_name}
    **Files**: {file_count} files, {total_lines} lines
    **Languages**: {languages}

    **File Contents**:
    {file_contents}

    Please provide a concise summary covering:
    - Project purpose and main functionality
    - Key components and their roles
    - Architecture and design patterns used
    - Important dependencies and integrations
    - Notable features or unique aspects

    Keep the summary focused and relevant for code analysis tasks.""",
                description="Summarize project context for AI analysis",
                required_variables=["project_name", "file_count", "total_lines", "languages", "file_contents"],
                system_prompt="You are analyzing a codebase to provide context for AI-assisted development. Focus on the most relevant architectural and functional aspects."
            ),
            
            "alpha_codium": PromptTemplate(
                name="alpha_codium",
                template="""You are implementing a solution using AlphaCodium methodology.

    ## Task Description
    {goal}

    ## Project Context
    {project_context}

    ## AlphaCodium Process

    ### Phase 1: Problem Analysis
    1. Understand the core requirements
    2. Identify key technical challenges
    3. Break down into sub-problems
    4. Determine success criteria

    ### Phase 2: Solution Design
    1. Design modular architecture
    2. Plan component interfaces
    3. Consider edge cases and error handling
    4. Define testing strategy

    ### Phase 3: Implementation
    Generate production-ready code with:
    - Clear modular structure
    - Comprehensive error handling
    - Inline documentation
    - Type safety where applicable

    ### Phase 4: Self-Validation
    - Verify all requirements are met
    - Check for potential bugs
    - Ensure code quality standards

    Generate your complete implementation now:""",
                description="Comprehensive enterprise-grade code generation",
                required_variables=["goal", "project_context"],
                max_context_length=15000,
                system_prompt="You are a senior software architect generating enterprise-grade, production-ready implementations using research-validated methodologies including SoA task decomposition and CodeJudge semantic validation."
            ),
            
            # ==========================================
            # ⭐ NEW: Aider統合専用テンプレート（Phase 1追加）
            # ==========================================
            
            "aider_code_generation": PromptTemplate(
                name="aider_code_generation",
                template="""Act as an expert {language} developer.
    Always use best practices when coding.
    Respect and use existing conventions, libraries, etc that are already present in the code base.

    CRITICAL OUTPUT FORMAT RULES:
    - ALWAYS respond in PLAIN MARKDOWN format
    - NEVER use JSON, YAML, or any structured data format for code
    - NEVER wrap code in JSON strings
    - NEVER use escaped quotes (\") or escaped newlines (\\n) in code

    Code format requirements:
    ```{language} filename.ext
    # actual code here (no escaping, no JSON)
    ```

    FORBIDDEN FORMATS:
    {{
    "files": [...]  ❌ NEVER do this
    }}

    REQUIRED FORMAT:
    ```python main.py
    def hello():
        print("Hello")
    ```  ✅ ALWAYS do this

    ---

    Goal: {goal}

    Analysis:
    {analysis}

    Implementation Plan:
    {plan}

    Additional Context:
    {context}

    ---

    Generate clean, working code now. Each file must be in plain markdown format.
    If you need to create multiple files, use multiple code blocks like:

    ```{language} file1.ext
    # code for file 1
    ```

    ```{language} file2.ext
    # code for file 2
    ```

    Do NOT add explanatory text between code blocks.""",
                description="Aider-optimized code generation (JSON-free, plain markdown only)",
                required_variables=["language", "goal", "analysis", "plan", "context"],
                max_context_length=15000,
                system_prompt="You are an expert software developer. Generate clean, working code in plain markdown format. NEVER use JSON or structured formats."
            ),
            
            # ==========================================
            # ⭐ NEW: Multi-Stage Phase 2 Template (for Phase 2 generation)
            # ==========================================
            
            "multi_stage_phase2": PromptTemplate(
                name="multi_stage_phase2",
                template="""Generate application layer code based on the foundation layer created in Phase 1.

**Original Goal**: {original_goal}

**Phase 1 Generated Files (Foundation Layer)**:
{phase1_context}

**Language**: {detected_language}
**Project Type**: {project_type}

CRITICAL INSTRUCTIONS FOR PHASE 2:

## 1. Foundation Layer Integration
- CAREFULLY REVIEW the Phase 1 files above before generating any code
- Pay special attention to how configuration is structured (class attributes vs module variables)
- If Phase 1 generated config.py:
  * Check what attributes are defined in the Config class
  * If you need to access config.SOME_VALUE, verify SOME_VALUE exists as a class attribute
  * If it's only a module variable, import it directly: from config.config import SOME_VALUE

## 2. Cross-Phase Consistency
- Maintain the same naming conventions established in Phase 1
- Use the same import patterns established in Phase 1
- Reference models, schemas, and config exactly as they are defined in Phase 1
- Do NOT assume attributes exist without verifying them in the Phase 1 code above

## 3. Application Layer Requirements
{phase2_specific_requirements}

## 4. Attribute Access Pattern Verification
Before writing any line that accesses an attribute from Phase 1 files:
- Step 1: Locate the definition in the Phase 1 code above
- Step 2: Verify it's accessible via your intended access pattern
- Step 3: If not accessible, adjust your code to match the actual definition

Generate production-ready application layer code now, ensuring perfect consistency with Phase 1.""",
                description="Multi-stage generation Phase 2 with explicit Phase 1 integration",
                required_variables=["original_goal", "phase1_context", "detected_language", "project_type", "phase2_specific_requirements"],
                max_context_length=20000,
                system_prompt="You are an expert software developer creating Phase 2 of a multi-stage implementation. You MUST carefully review Phase 1 code and ensure perfect consistency with established patterns, especially configuration access patterns."
            ),
            
            # ==========================================
            # ⭐ NEW: Python Best Practices Template
            # ==========================================
            
            "python_best_practices": PromptTemplate(
                name="python_best_practices",
                template="""Generate Python code following these mandatory best practices:

## Configuration Pattern
```python
# config.py structure
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = os.path.join(BASE_DIR, 'db.sqlite')

class Config:
    # ALWAYS define as class attributes if accessed via instances
    BASE_DIR = BASE_DIR
    DATABASE_PATH = DATABASE_PATH
    DATABASE_URI = f"sqlite:///{DATABASE_PATH}"
    DEBUG = False
    
class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

def get_config(env='development'):
    configs = {
        'development': DevelopmentConfig,
        'production': ProductionConfig
    }
    return configs.get(env, DevelopmentConfig)
```

## Common Pitfalls to AVOID
1. ❌ Module variable used as class attribute without defining it
2. ❌ Circular imports (use late imports or dependency injection)
3. ❌ Mutable default arguments (def func(items=[]):)
4. ❌ Bare except clauses (use specific exceptions)

## Type Hints (MANDATORY)
- All function arguments and return values
- Class attributes
- Example:
  ```python
  from typing import Optional, Dict, Any
  
  class Database:
      db_path: str
      
      def __init__(self, db_path: Optional[str] = None):
          self.db_path = db_path or "default.db"
      
      def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
          ...
  ```

Generate code following these patterns:
{code_requirements}""",
                description="Python-specific best practices and common pitfall prevention",
                required_variables=["code_requirements"],
                max_context_length=10000,
                system_prompt="You are a Python expert who strictly follows PEP 8 and modern Python best practices. You prevent common pitfalls and ensure type safety."
            ),
            
            # ==========================================
            # ⭐ NEW: Problem Analysis Template (for /think command)
            # ==========================================
            
            "problem_analysis": PromptTemplate(
                name="problem_analysis",
                template="""Analyze the following development goal and break it down systematically.

    ## Goal
    {goal}

    ## Analysis Tasks

    ### 1. Requirement Understanding
    - What is the core objective?
    - What are the key features and functionalities?
    - What are the constraints and requirements?

    ### 2. Technical Breakdown
    - What technologies/frameworks are needed?
    - What are the main components or modules?
    - What are the technical challenges?

    ### 3. Architecture Planning
    - What is the overall system structure?
    - How should components interact?
    - What are the key design decisions?

    ### 4. Implementation Approach
    - What is the development sequence?
    - What are the dependencies between components?
    - What are the critical paths?

    ### 5. Risk Assessment
    - What could go wrong?
    - What are the potential bottlenecks?
    - What requires special attention?

    Please provide a comprehensive analysis covering these aspects.""",
                description="Analyze development goals and break down requirements",
                required_variables=["goal"],
                max_context_length=8000,
                system_prompt="You are a senior software architect analyzing development requirements. Provide clear, structured analysis that will guide implementation planning."
            ),
            
            # ==========================================
            # ⭐ NEW: Implementation Planning Template (for /plan command)
            # ==========================================
            
            "implementation_plan": PromptTemplate(
                name="implementation_plan",
                template="""Create a detailed implementation plan based on the analysis.

    ## Goal
    {goal}

    ## Analysis Results
    {analysis}

    ## Planning Tasks

    ### 1. Architecture Design
    - Define the overall system architecture
    - Identify main components and their responsibilities
    - Design interfaces and contracts between components

    ### 2. File Structure
    - List all files that need to be created
    - Organize files into logical directories
    - Define naming conventions

    ### 3. Implementation Sequence
    - Break down into implementable steps
    - Define dependencies between steps
    - Prioritize based on criticality and dependencies

    ### 4. Technology Stack
    - Specify frameworks and libraries
    - Define versions and compatibility requirements
    - List any tools or utilities needed

    ### 5. Key Implementation Details
    - Outline core algorithms or logic
    - Define data structures and models
    - Specify error handling strategies
    - Plan testing approach

    ### 6. Potential Challenges
    - Identify technical risks
    - Plan mitigation strategies
    - Note areas requiring special attention

    Please provide a concrete, actionable implementation plan.""",
                description="Create implementation plans from analysis results",
                required_variables=["goal", "analysis"],
                max_context_length=10000,
                system_prompt="You are a senior software architect creating detailed implementation plans. Provide concrete, actionable steps that developers can follow to implement the solution."
            ),

            # ==========================================
            # ファイル操作用テンプレート
            # ==========================================
            
            "edit_file": PromptTemplate(
                name="edit_file",
                template="""Edit the file '{filename}' according to the following instruction:

Current content:
```
{current_content}
```

Instruction: {instruction}

Please provide the modified file content according to the instruction.

Requirements:
- Return ONLY the complete updated file content
- Do NOT include explanations or comments outside the code
- Preserve the file structure unless explicitly asked to change it
- Maintain code quality and best practices
- If the instruction is unclear, make reasonable assumptions

Modified file content:""",
                description="Edit a file based on user instruction",
                required_variables=["filename", "current_content", "instruction"],
                system_prompt="You are an expert code editor. Modify files according to user instructions while maintaining quality and correctness. Always return complete, executable code."
            ),
            
            "edit_system": PromptTemplate(
                name="edit_system",
                template="You are an expert code editor. Modify files according to user instructions while maintaining quality and correctness. Always return complete, executable code.",
                description="System prompt for file editing",
                required_variables=[]
            ),
            
            "fix_file": PromptTemplate(
                name="fix_file",
                template="""Analyze and fix issues in the file '{filename}':

Current content:
```
{current_content}
```

Please fix any issues including:
- Syntax errors and typos
- Logic errors and bugs
- Code style issues (follow language conventions)
- Best practices violations
- Potential security vulnerabilities
- Performance issues

Requirements:
- Return ONLY the fixed file content
- Do NOT include explanations or comments outside the code
- Fix ALL identified issues
- Preserve functionality unless the code is fundamentally broken
- Add inline comments only for complex fixes

Fixed file content:""",
                description="Fix issues in a file",
                required_variables=["filename", "current_content"],
                system_prompt="You are an expert code fixer. Identify and fix all issues in the provided code. Return complete, working code."
            ),
            
            "fix_system": PromptTemplate(
                name="fix_system",
                template="You are an expert code fixer. Identify and fix all issues in the provided code. Return complete, working code.",
                description="System prompt for file fixing",
                required_variables=[]
            ),
            
            "review_code": PromptTemplate(
                name="review_code",
                template="""Review the code in '{target}' ({files_count} file(s)):

{files_content}

Please provide a comprehensive code review covering:

1. **Code Quality**
   - Readability and maintainability
   - Code organization and structure
   - Naming conventions
   - Comments and documentation

2. **Functionality**
   - Correctness and logic
   - Edge cases and error handling
   - Potential bugs or issues

3. **Best Practices**
   - Language-specific conventions
   - Design patterns
   - SOLID principles adherence

4. **Security**
   - Potential vulnerabilities
   - Input validation
   - Authentication/authorization issues

5. **Performance**
   - Optimization opportunities
   - Resource usage
   - Algorithmic efficiency

6. **Suggestions**
   - Specific improvements
   - Alternative approaches
   - Refactoring recommendations

Provide your review in a clear, structured format with specific examples and line references where applicable.""",
                description="Review code files",
                required_variables=["target", "files_count", "files_content"],
                system_prompt="You are an expert code reviewer. Provide thorough, constructive feedback on code quality, security, and best practices. Be specific and cite examples."
            ),
            
            "review_system": PromptTemplate(
                name="review_system",
                template="You are an expert code reviewer. Provide thorough, constructive feedback on code quality, security, and best practices. Be specific and cite examples.",
                description="System prompt for code review",
                required_variables=[]
            ),
        }
    
    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """Get a prompt template by name"""
        return self.templates.get(name)
    
    def get_prompt(self, name: str) -> str:
        """Get a prompt template string by name (for backward compatibility)
        
        This method provides a simpler interface for accessing template strings
        directly, which is useful when templates are used with .format() directly.
        
        Args:
            name: Template name
            
        Returns:
            Template string if found, or system_prompt for system templates
        
        Example:
            >>> manager.get_prompt("edit_file").format(filename="test.py", ...)
            >>> manager.get_prompt("edit_system")  # Returns system prompt directly
        """
        template = self.get_template(name)
        if not template:
            # Return a helpful error message
            return f"ERROR: Template '{name}' not found. Available templates: {', '.join(self.templates.keys())}"
        
        # For system prompts (templates ending with '_system'), return the system_prompt directly
        # This allows: system_prompt=prompt_manager.get_prompt("edit_system")
        if name.endswith('_system'):
            if template.system_prompt:
                return template.system_prompt
            elif template.template:
                # Fallback to template if system_prompt is not defined
                return template.template
        
        # For regular templates, return the template string
        # This allows: prompt = prompt_manager.get_prompt("edit_file").format(...)
        return template.template
    
    def render_prompt(self, template_name: str, variables: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Render a prompt template with provided variables"""
        template = self.get_template(template_name)
        if not template:
            return None
        
        # Check required variables
        missing_vars = [var for var in template.required_variables if var not in variables]
        if missing_vars:
            raise ValueError(f"Missing required variables for template '{template_name}': {missing_vars}")
        
        # Set defaults for optional variables
        render_vars = variables.copy()
        if template.optional_variables:
            for var in template.optional_variables:
                if var not in render_vars:
                    render_vars[var] = ""
        
        # Render the template
        try:
            prompt = template.template.format(**render_vars)
            
            # Truncate if too long
            if len(prompt) > template.max_context_length:
                truncation_point = template.max_context_length - 100
                prompt = prompt[:truncation_point] + "\n\n[Content truncated for length...]"
            
            return {
                "prompt": prompt,
                "system_prompt": template.system_prompt or "",
                "template_name": template_name
            }
            
        except KeyError as e:
            raise ValueError(f"Template variable not provided: {e}")
    
    def list_templates(self) -> List[Dict[str, str]]:
        """List all available templates"""
        return [
            {
                "name": template.name,
                "description": template.description,
                "required_variables": template.required_variables,
                "optional_variables": template.optional_variables or []
            }
            for template in self.templates.values()
        ]
    
    def add_template(self, template: PromptTemplate):
        """Add a custom template"""
        self.templates[template.name] = template
    
    def has_template(self, name: str) -> bool:
        return name in self.templates

    def smart_truncate(self, text: str, max_length: int, preserve_structure: bool = True) -> str:
        """Intelligently truncate text while preserving structure"""
        if len(text) <= max_length:
            return text
        
        if not preserve_structure:
            return text[:max_length - 20] + "\n[... truncated ...]"
        
        # Try to truncate at logical boundaries
        truncation_point = max_length - 50
        
        # Look for good truncation points (paragraph breaks, function boundaries, etc.)
        boundaries = ['\n\n', '\ndef ', '\nclass ', '\n# ', '\n## ']
        
        best_point = truncation_point
        for boundary in boundaries:
            last_occurrence = text.rfind(boundary, 0, truncation_point)
            if last_occurrence > truncation_point * 0.7:  # Don't truncate too early
                best_point = last_occurrence
                break
        
        return text[:best_point] + f"\n\n[... {len(text) - best_point} characters truncated ...]"


# Global instance
prompt_manager = PromptTemplateManager()