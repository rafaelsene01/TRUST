"""TRUST grounding adapters.

Available in MVP:
    filesystem — reads from local disk

Coming in v1.1:
    notion    — reads from Notion API
    http      — reads from Confluence/Wiki/any HTTP source
"""

from .filesystem_adapter import FilesystemAdapter

__all__ = ["FilesystemAdapter"]
