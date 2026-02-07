#!/usr/bin/env python3
"""
Cognix MCP Server

Provides MCP (Model Context Protocol) server functionality,
exposing Cognix's advanced analysis capabilities to Claude Desktop,
Cursor, VSCode, and other MCP-compatible tools.

Available Tools:
1. analyze_impact - Analyze file change impact
2. get_repository_summary - Get repository understanding
3. prepare_safe_edit - Prepare safe file edit
4. execute_safe_edit - Execute prepared edit
5. rollback_edit - Rollback an edit
6. search_repository_files - Search repository files
7. get_dependency_graph - Get dependency graph

Usage:
    # Start MCP server (stdio mode)
    cognix-mcp
    
    # Or via main.py
    python -m cognix.main --mcp
"""

import asyncio
import logging
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

# Configure logging to stderr (important for MCP stdio mode)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Disable verbose HTTP logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# MCP SDK imports
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    logger.error("Error: MCP SDK not installed.")
    logger.error("Install with: pip install mcp>=1.0.0")
    sys.exit(1)

# Cognix imports
from cognix.config import Config
from cognix.memory import Memory
from cognix.repository_manager import RepositoryManager
from cognix.impact_analyzer import ImpactAnalyzer
from cognix.safe_editor import SafeEditor, EditContext
from cognix.enhanced_memory import EnhancedMemory

# Initialize FastMCP server
mcp = FastMCP("cognix")

# Global Cognix components (initialized on startup)
config: Optional[Config] = None
memory: Optional[Memory] = None
repository_manager: Optional[RepositoryManager] = None
impact_analyzer: Optional[ImpactAnalyzer] = None
safe_editor: Optional[SafeEditor] = None
_initialized = False


def initialize_cognix():
    """Initialize Cognix components (synchronous)"""
    global config, memory, repository_manager, impact_analyzer, safe_editor, _initialized
    
    if _initialized:
        return
    
    try:
        logger.info("Initializing Cognix components...")
        
        # 1. Config
        config = Config()
        logger.info("✓ Config initialized")
        
        # 2. Memory (try EnhancedMemory first)
        try:
            memory = EnhancedMemory()
            if hasattr(memory, 'enable_repository_features'):
                memory.enable_repository_features()
            logger.info("✓ EnhancedMemory initialized")
        except Exception as e:
            logger.warning(f"EnhancedMemory unavailable, using standard Memory: {e}")
            memory = Memory()
            logger.info("✓ Standard Memory initialized")
        
        # 3. Repository Manager
        project_root = Path.cwd()
        repository_manager = RepositoryManager(memory, project_root)
        logger.info(f"✓ RepositoryManager initialized (root: {project_root})")
        
        # 4. Impact Analyzer
        impact_analyzer = ImpactAnalyzer(
            repository_analyzer=repository_manager,
            config=config
        )
        logger.info("✓ ImpactAnalyzer initialized")
        
        # 5. Safe Editor
        safe_editor = SafeEditor(
            memory,
            impact_analyzer=impact_analyzer,
            repository_manager=repository_manager
        )
        logger.info("✓ SafeEditor initialized")
        
        _initialized = True
        logger.info("Cognix components initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Cognix components: {e}")
        logger.error(traceback.format_exc())
        raise


def ensure_initialized():
    """Ensure Cognix components are initialized"""
    if not _initialized:
        initialize_cognix()


# ============================================================================
# MCP Tool Implementations
# ============================================================================

@mcp.tool()
def analyze_impact(file_path: str, change_type: str = "modify") -> Dict[str, Any]:
    """
    Analyze the impact of file changes.
    
    This tool analyzes how changes to a file will affect other parts of the codebase.
    It provides dependency information, affected files, and risk assessment.
    
    Args:
        file_path: Path to the file to analyze (relative or absolute)
        change_type: Type of change - "add", "modify", or "delete" (default: "modify")
    
    Returns:
        Dictionary containing impact analysis results including risk_level, 
        affected_files, and recommendations.
    """
    ensure_initialized()
    
    try:
        if not impact_analyzer:
            raise RuntimeError("ImpactAnalyzer not initialized")
        
        # Convert to absolute path if relative
        file_path_obj = Path(file_path)
        if not file_path_obj.is_absolute():
            file_path_obj = Path.cwd() / file_path_obj
        
        file_path_str = str(file_path_obj)
        
        result = impact_analyzer.analyze_change_impact(file_path_str, change_type)
        
        logger.info(f"Impact analysis completed for {file_path}: risk={result.get('risk_level')}")
        return result
        
    except Exception as e:
        logger.error(f"Error in analyze_impact: {e}")
        return {
            "error": True,
            "error_message": str(e),
            "target_file": file_path,
            "change_type": change_type
        }


@mcp.tool()
def get_repository_summary() -> Dict[str, Any]:
    """
    Get comprehensive repository understanding summary.
    
    Returns persistent repository analysis including file structure,
    language statistics, and overall project understanding.
    
    Returns:
        Dictionary containing total_files, total_size_bytes, total_lines,
        languages distribution, key_files, and last_updated timestamp.
    """
    ensure_initialized()
    
    try:
        if not repository_manager:
            raise RuntimeError("RepositoryManager not initialized")
        
        result = repository_manager.get_project_summary()
        
        logger.info("Repository summary retrieved")
        return result
        
    except Exception as e:
        logger.error(f"Error in get_repository_summary: {e}")
        return {
            "error": True,
            "error_message": str(e),
            "total_files": 0,
            "languages": {}
        }


@mcp.tool()
def prepare_safe_edit(file_path: str, proposed_content: str) -> Dict[str, Any]:
    """
    Prepare a safe file edit with impact analysis.
    
    Analyzes the proposed changes and creates a safe edit context with:
    - Automatic backup creation
    - Risk level assessment
    - Impact analysis
    - Safety recommendations
    
    Args:
        file_path: Path to the file to edit
        proposed_content: Proposed new file content
    
    Returns:
        Dictionary containing edit_id, risk_level, affected_files, and safety_checks.
    """
    ensure_initialized()
    
    try:
        if not safe_editor:
            raise RuntimeError("SafeEditor not initialized")
        
        # Convert to absolute path
        file_path_obj = Path(file_path)
        if not file_path_obj.is_absolute():
            file_path_obj = Path.cwd() / file_path_obj
        
        file_path_str = str(file_path_obj)
        
        edit_context = safe_editor.prepare_safe_edit(file_path_str, proposed_content)
        
        result = edit_context.to_dict()
        logger.info(f"Safe edit prepared for {file_path}: risk={result.get('risk_level')}")
        return result
        
    except Exception as e:
        logger.error(f"Error in prepare_safe_edit: {e}")
        return {
            "error": True,
            "error_message": str(e),
            "file_path": file_path
        }


@mcp.tool()
def execute_safe_edit(edit_id: str, file_path: str, original_content: str, 
                      proposed_content: str, backup_path: str, 
                      risk_level: str = "low") -> Dict[str, Any]:
    """
    Execute a prepared safe edit.
    
    Applies the edit that was prepared with prepare_safe_edit.
    Creates automatic backup before applying changes.
    
    Args:
        edit_id: Unique identifier for this edit
        file_path: Target file path
        original_content: Original file content
        proposed_content: Proposed new content
        backup_path: Path to backup file
        risk_level: Risk level from prepare_safe_edit
    
    Returns:
        Dictionary containing success status, file_path, and backup_path.
    """
    ensure_initialized()
    
    try:
        if not safe_editor:
            raise RuntimeError("SafeEditor not initialized")
        
        # Reconstruct EditContext from parameters
        edit_context_dict = {
            "edit_id": edit_id,
            "file_path": file_path,
            "original_content": original_content,
            "proposed_content": proposed_content,
            "backup_path": backup_path,
            "risk_level": risk_level
        }
        
        edit_context = EditContext.from_dict(edit_context_dict)
        
        result = safe_editor.execute_safe_edit(edit_context)
        
        logger.info(f"Safe edit executed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in execute_safe_edit: {e}")
        return {
            "success": False,
            "error": True,
            "error_message": str(e)
        }


@mcp.tool()
def rollback_edit(edit_id: str) -> Dict[str, Any]:
    """
    Rollback a previously executed edit.
    
    Reverts a file to its state before an edit was applied.
    
    Args:
        edit_id: Edit identifier from execute_safe_edit
    
    Returns:
        Dictionary containing success status and message.
    """
    ensure_initialized()
    
    try:
        if not safe_editor:
            raise RuntimeError("SafeEditor not initialized")
        
        result = safe_editor.rollback_edit(edit_id)
        
        logger.info(f"Edit rollback: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in rollback_edit: {e}")
        return {
            "success": False,
            "error": True,
            "error_message": str(e)
        }


@mcp.tool()
def search_repository_files(query: str) -> List[Dict[str, Any]]:
    """
    Search repository files by various criteria.
    
    Searches through analyzed repository files by file path, 
    function names, class names, and dependencies.
    
    Args:
        query: Search query string
    
    Returns:
        List of matching files with file_path, language, and other metadata.
    """
    ensure_initialized()
    
    try:
        if not memory or not hasattr(memory, 'search_repository_files'):
            # Fallback to basic search if EnhancedMemory not available
            return []
        
        results = memory.search_repository_files(query)
        
        # Convert RepositoryFile objects to dictionaries
        results_dict = [repo_file.to_dict() for repo_file in results]
        
        logger.info(f"Search completed: {len(results_dict)} results for '{query}'")
        return results_dict
        
    except Exception as e:
        logger.error(f"Error in search_repository_files: {e}")
        return []


@mcp.tool()
def get_dependency_graph(file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Get dependency graph for a file or entire project.
    
    Returns dependency relationships including direct dependencies 
    (files this file imports) and reverse dependencies (files that import this file).
    
    Args:
        file_path: Optional file path. If None, returns entire project graph.
    
    Returns:
        Dictionary containing file_path, direct_dependencies, 
        reverse_dependencies, and dependency_count.
    """
    ensure_initialized()
    
    try:
        if not impact_analyzer:
            raise RuntimeError("ImpactAnalyzer not initialized")
        
        if file_path:
            # Get dependencies for specific file
            file_path_obj = Path(file_path)
            if not file_path_obj.is_absolute():
                file_path_obj = Path.cwd() / file_path_obj
            file_path_str = str(file_path_obj)
            
            direct_deps = impact_analyzer.get_direct_dependencies(file_path_str)
            reverse_deps = impact_analyzer.get_reverse_dependencies(file_path_str)
            
            result = {
                "file_path": file_path_str,
                "direct_dependencies": sorted(list(direct_deps)),
                "reverse_dependencies": sorted(list(reverse_deps)),
                "dependency_count": len(direct_deps) + len(reverse_deps)
            }
        else:
            # Get entire project dependency graph
            result = {
                "file_path": "entire_project",
                "dependency_graph": {k: list(v) for k, v in impact_analyzer.dependency_cache.items()},
                "total_files": len(impact_analyzer.dependency_cache)
            }
        
        logger.info(f"Dependency graph retrieved for: {file_path or 'entire_project'}")
        return result
        
    except Exception as e:
        logger.error(f"Error in get_dependency_graph: {e}")
        return {
            "error": True,
            "error_message": str(e),
            "file_path": file_path or "entire_project"
        }


# ============================================================================
# MCP Server Entry Point
# ============================================================================

def main():
    """Main entry point for MCP server"""
    try:
        logger.info("Starting Cognix MCP Server...")
        
        # Initialize Cognix components
        initialize_cognix()
        
        logger.info("Cognix MCP Server ready")
        logger.info("Available tools: analyze_impact, get_repository_summary, "
                   "prepare_safe_edit, execute_safe_edit, rollback_edit, "
                   "search_repository_files, get_dependency_graph")
        
        # Run FastMCP server
        mcp.run()
            
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()