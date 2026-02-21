#!/usr/bin/env python3
"""
Task Manager CLI - Plugin system.
Hook-based plugin architecture for extensibility.
"""

from typing import Callable, List, Dict, Any, Optional


class PluginHook:
    """A single hook point that plugins can register callbacks on."""

    def __init__(self, name: str):
        self.name = name
        self._callbacks: List[Callable] = []

    def register(self, callback: Callable):
        """Register a callback for this hook."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister(self, callback: Callable):
        """Unregister a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def fire(self, **kwargs) -> List[Any]:
        """Fire all registered callbacks with the given kwargs.
        Returns list of results from each callback.
        """
        results = []
        for cb in self._callbacks:
            try:
                result = cb(**kwargs)
                results.append(result)
            except Exception as e:
                results.append({"error": str(e)})
        return results

    @property
    def callback_count(self) -> int:
        return len(self._callbacks)


class PluginManager:
    """Manages plugin hooks for the task manager."""

    # Standard hook names
    HOOK_TASK_PRE_CREATE = "task_pre_create"
    HOOK_TASK_POST_CREATE = "task_post_create"
    HOOK_TASK_PRE_UPDATE = "task_pre_update"
    HOOK_TASK_POST_UPDATE = "task_post_update"
    HOOK_TASK_PRE_DELETE = "task_pre_delete"
    HOOK_TASK_POST_DELETE = "task_post_delete"
    HOOK_TASK_STATUS_CHANGE = "task_status_change"
    HOOK_EXPORT_PRE = "export_pre"
    HOOK_EXPORT_POST = "export_post"

    def __init__(self):
        self._hooks: Dict[str, PluginHook] = {}
        # Register all standard hooks
        for name in [
            self.HOOK_TASK_PRE_CREATE, self.HOOK_TASK_POST_CREATE,
            self.HOOK_TASK_PRE_UPDATE, self.HOOK_TASK_POST_UPDATE,
            self.HOOK_TASK_PRE_DELETE, self.HOOK_TASK_POST_DELETE,
            self.HOOK_TASK_STATUS_CHANGE,
            self.HOOK_EXPORT_PRE, self.HOOK_EXPORT_POST,
        ]:
            self._hooks[name] = PluginHook(name)

    def get_hook(self, name: str) -> Optional[PluginHook]:
        """Get a hook by name."""
        return self._hooks.get(name)

    def register(self, hook_name: str, callback: Callable):
        """Register a callback on a named hook."""
        hook = self._hooks.get(hook_name)
        if hook is None:
            hook = PluginHook(hook_name)
            self._hooks[hook_name] = hook
        hook.register(callback)

    def fire(self, hook_name: str, **kwargs) -> List[Any]:
        """Fire a named hook."""
        hook = self._hooks.get(hook_name)
        if hook is None:
            return []
        return hook.fire(**kwargs)

    def list_hooks(self) -> List[str]:
        """List all registered hook names."""
        return sorted(self._hooks.keys())

    def get_stats(self) -> Dict[str, int]:
        """Get callback count per hook."""
        return {name: hook.callback_count for name, hook in self._hooks.items()}


# Global plugin manager instance
plugin_manager = PluginManager()
