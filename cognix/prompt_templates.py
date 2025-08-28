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
            
            "code_review": PromptTemplate(
                name="code_review",
                template="""Please provide a comprehensive code review for the following {content_type}:

{context_info}

Code to review:
```{language}
{code_content}
```

Please analyze and provide feedback on:

1. **Code Quality**: Structure, readability, maintainability
2. **Best Practices**: Adherence to language conventions and patterns
3. **Performance**: Potential optimizations and efficiency improvements
4. **Security**: Vulnerability assessment and security considerations
5. **Architecture**: Design patterns and architectural decisions
6. **Testing**: Testability and potential test cases
7. **Documentation**: Code comments and documentation quality

For each area, provide:
- Specific observations
- Actionable recommendations
- Priority level (High/Medium/Low)

Be constructive and specific in your feedback.""",
                description="Comprehensive code review",
                required_variables=["content_type", "context_info", "code_content"],
                optional_variables=["language"],
                system_prompt="You are a senior code reviewer with expertise across multiple programming languages and best practices. Provide constructive, actionable feedback."
            ),
            
            "problem_analysis": PromptTemplate(
                name="problem_analysis",
                template="""Analyze the following development goal and provide a comprehensive breakdown:

**Goal**: {goal}

Please provide a thorough analysis covering:

## 1. Problem Breakdown
- Core requirements and objectives
- Key challenges and constraints
- Success criteria and acceptance criteria

## 2. Technical Considerations
- Recommended technology stack and tools
- Architecture and design patterns
- Performance and scalability requirements
- Security and compliance considerations

## 3. Implementation Approach
- High-level development strategy
- Key components and modules needed
- Integration points and dependencies
- Risk assessment and mitigation strategies

## 4. Resource Requirements
- Estimated development effort
- Required skills and expertise
- External dependencies and APIs
- Infrastructure and deployment needs

## 5. Potential Challenges
- Technical difficulties and solutions
- Common pitfalls and how to avoid them
- Alternative approaches to consider

Be thorough but concise. This analysis will guide the implementation planning phase.""",
                description="Analyze development goals and requirements",
                required_variables=["goal"],
                system_prompt="You are a technical architect with expertise in system design, development planning, and risk assessment. Provide comprehensive analysis to guide implementation decisions."
            ),
            
            "implementation_plan": PromptTemplate(
                name="implementation_plan",
                template="""Based on the following analysis, create a detailed implementation plan:

**Goal**: {goal}

**Analysis**:
{analysis}

Please create a structured implementation plan:

## 1. Development Phases
Break down the implementation into logical phases with:
- Phase objectives and deliverables
- Dependencies between phases
- Estimated timeline and effort

## 2. Technical Architecture
- System components and their relationships
- Data flow and integration points
- Technology stack decisions with rationale

## 3. File Structure and Organization
- Directory structure and file organization
- Module dependencies and interfaces
- Configuration and environment setup

## 4. Implementation Steps
Detailed step-by-step implementation guide:
- Numbered list of concrete actions
- Prerequisites for each step
- Validation and testing checkpoints

## 5. Testing Strategy
- Unit testing approach and coverage
- Integration testing scenarios
- Performance and security testing plans

## 6. Deployment and Operations
- Deployment strategy and environment setup
- Monitoring and logging requirements
- Maintenance and update procedures

Make the plan actionable and specific enough to guide development.""",
                description="Create detailed implementation plans",
                required_variables=["goal", "analysis"],
                system_prompt="You are a technical lead creating detailed implementation plans. Provide specific, actionable guidance that developers can follow to successfully build the system."
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
            )
        }
    
    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """Get a prompt template by name"""
        return self.templates.get(name)
    
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