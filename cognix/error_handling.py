"""
Enhanced error handling framework for Cognix
Provides consistent error handling patterns and user-friendly error messages
"""

import sys
import traceback
from typing import Optional, Dict, Any, Type
from pathlib import Path
from enum import Enum


class ErrorLevel(Enum):
    """Error severity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class CognixError(Exception):
    """Base exception class for Cognix-specific errors"""
    
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "COGNIX_ERROR"
        self.details = details or {}
        self.level = ErrorLevel.ERROR


class FileOperationError(CognixError):
    """Errors related to file operations"""
    
    def __init__(self, message: str, file_path: str = None, operation: str = None):
        super().__init__(message, "FILE_OPERATION_ERROR")
        self.file_path = file_path
        self.operation = operation


class LLMError(CognixError):
    """Errors related to LLM operations"""
    
    def __init__(self, message: str, provider: str = None, model: str = None):
        super().__init__(message, "LLM_ERROR")
        self.provider = provider
        self.model = model


class SessionError(CognixError):
    """Errors related to session management"""
    
    def __init__(self, message: str, session_name: str = None):
        super().__init__(message, "SESSION_ERROR")
        self.session_name = session_name


class ConfigurationError(CognixError):
    """Errors related to configuration"""
    
    def __init__(self, message: str, config_key: str = None):
        super().__init__(message, "CONFIG_ERROR")
        self.config_key = config_key


class ValidationError(CognixError):
    """Errors related to input validation"""
    
    def __init__(self, message: str, field: str = None, value: Any = None):
        super().__init__(message, "VALIDATION_ERROR")
        self.field = field
        self.value = value


class ErrorHandler:
    """Central error handling and logging"""
    
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self.error_history = []
    
    def handle_error(self, error: Exception, context: str = None) -> bool:
        """
        Handle an error with appropriate logging and user feedback
        Returns True if the error was handled gracefully, False if it should propagate
        """
        if isinstance(error, CognixError):
            return self._handle_cognix_error(error, context)
        else:
            return self._handle_system_error(error, context)
    
    def _handle_cognix_error(self, error: CognixError, context: str = None) -> bool:
        """Handle Cognix-specific errors"""
        error_info = {
            "type": type(error).__name__,
            "message": error.message,
            "code": error.error_code,
            "context": context,
            "details": error.details
        }
        
        self.error_history.append(error_info)
        
        # Display user-friendly error message
        print(f"\n❌ {error.message}")
        
        if isinstance(error, FileOperationError):
            if error.file_path:
                print(f"   File: {error.file_path}")
            if error.operation:
                print(f"   Operation: {error.operation}")
                
        elif isinstance(error, LLMError):
            if error.provider:
                print(f"   Provider: {error.provider}")
            if error.model:
                print(f"   Model: {error.model}")
            print("   💡 Try switching to a different model with /model <name>")
                
        elif isinstance(error, SessionError):
            if error.session_name:
                print(f"   Session: {error.session_name}")
            print("   💡 Use /list-sessions to see available sessions")
                
        elif isinstance(error, ConfigurationError):
            if error.config_key:
                print(f"   Configuration key: {error.config_key}")
            print("   💡 Use /config to check your configuration")
                
        elif isinstance(error, ValidationError):
            if error.field and error.value:
                print(f"   Field '{error.field}' with value: {error.value}")
        
        # Show debug info if enabled
        if self.debug_mode and error.details:
            print(f"   Debug details: {error.details}")
        
        return True  # Handled gracefully
    
    def _handle_system_error(self, error: Exception, context: str = None) -> bool:
        """Handle system/library errors"""
        error_info = {
            "type": type(error).__name__,
            "message": str(error),
            "context": context,
            "traceback": traceback.format_exc() if self.debug_mode else None
        }
        
        self.error_history.append(error_info)
        
        # Provide contextual error messages
        if isinstance(error, FileNotFoundError):
            print(f"\n❌ File not found: {error.filename}")
            print("   💡 Check the file path and make sure the file exists")
            return True
            
        elif isinstance(error, PermissionError):
            print(f"\n❌ Permission denied: {error.filename}")
            print("   💡 Check file permissions or run with appropriate privileges")
            return True
            
        elif isinstance(error, OSError) and "No space left" in str(error):
            print("\n❌ No space left on device")
            print("   💡 Free up disk space and try again")
            return True
            
        elif isinstance(error, KeyboardInterrupt):
            print("\n\n⏹️  Operation cancelled by user")
            return True
            
        elif isinstance(error, ImportError):
            missing_module = str(error).split("'")[1] if "'" in str(error) else "unknown"
            print(f"\n❌ Missing required module: {missing_module}")
            print(f"   💡 Install with: pip install {missing_module}")
            return True
        
        # For unhandled errors, show generic message
        print(f"\n❌ Unexpected error: {type(error).__name__}")
        print(f"   {str(error)}")
        
        if context:
            print(f"   Context: {context}")
        
        if self.debug_mode:
            print(f"\n🐛 Debug traceback:")
            traceback.print_exc()
        else:
            print("   💡 Run with --verbose for detailed error information")
        
        return False  # Should propagate for unexpected errors
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get statistics about handled errors"""
        if not self.error_history:
            return {"total_errors": 0}
        
        error_types = {}
        for error in self.error_history:
            error_type = error["type"]
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            "total_errors": len(self.error_history),
            "error_types": error_types,
            "recent_errors": self.error_history[-5:]  # Last 5 errors
        }
    
    def clear_history(self):
        """Clear error history"""
        self.error_history.clear()


def safe_execute(func, *args, error_handler: ErrorHandler = None, context: str = None, **kwargs):
    """
    Safely execute a function with error handling
    """
    if error_handler is None:
        error_handler = ErrorHandler()
    
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if error_handler.handle_error(e, context):
            return None  # Error handled gracefully
        else:
            raise  # Re-raise if not handled


def validate_file_path(file_path: str, must_exist: bool = True) -> Path:
    """Validate and return a Path object, raising ValidationError if invalid"""
    try:
        path = Path(file_path)
        
        if must_exist and not path.exists():
            raise ValidationError(
                f"File does not exist: {file_path}",
                field="file_path",
                value=file_path
            )
        
        if must_exist and not path.is_file():
            raise ValidationError(
                f"Path is not a file: {file_path}",
                field="file_path", 
                value=file_path
            )
        
        return path
        
    except OSError as e:
        raise ValidationError(
            f"Invalid file path: {file_path} ({e})",
            field="file_path",
            value=file_path
        )


def validate_function_name(name: str) -> str:
    """Validate Python function name"""
    import keyword
    
    if not name:
        raise ValidationError("Function name cannot be empty", field="function_name", value=name)
    
    if not name.isidentifier():
        raise ValidationError(
            f"Invalid function name: {name}",
            field="function_name",
            value=name
        )
    
    if keyword.iskeyword(name):
        raise ValidationError(
            f"Function name cannot be a Python keyword: {name}",
            field="function_name",
            value=name
        )
    
    return name


def validate_session_name(name: str) -> str:
    """Validate session name"""
    if not name:
        raise ValidationError("Session name cannot be empty", field="session_name", value=name)
    
    if len(name) > 100:
        raise ValidationError(
            "Session name too long (max 100 characters)",
            field="session_name",
            value=name
        )
    
    # Remove dangerous characters
    safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_ ")
    if not all(c in safe_chars for c in name):
        raise ValidationError(
            "Session name contains invalid characters",
            field="session_name",
            value=name
        )
    
    return name.strip()