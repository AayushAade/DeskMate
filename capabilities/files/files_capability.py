import os
import re
from capabilities.base_capability import BaseCapability, Intent, CapabilityResult
from assistant.personality import mochi_voice
from events import event_bus

class FilesCapability(BaseCapability):
    @property
    def name(self) -> str:
        return "files"

    def match_and_extract(self, query: str) -> Intent | None:
        q = query.strip()
        
        # Look for a path ending in .txt or .md
        # Handles paths containing slashes, letters, numbers, hyphens, dots
        path_pattern = r'([A-Za-z0-9_\-\.\/\\~]+\.(?:txt|md))'
        match = re.search(path_pattern, q, re.IGNORECASE)
        
        if match:
            file_path = match.group(1)
            # Check if keywords like read, view, contents of, show exist in query
            has_intent_keywords = any(word in q.lower() for word in ["read", "view", "show", "open", "contents"])
            
            return Intent(
                capability=self.name,
                confidence=0.95 if has_intent_keywords else 0.70,
                parameters={"file_path": file_path}
            )
            
        return None

    def execute(self, params: dict) -> CapabilityResult:
        raw_path = params.get("file_path", "").strip()
        if not raw_path:
            return CapabilityResult(
                success=False,
                data={"error": "No file path provided"},
                message="Meow... I couldn't read the file because the path was empty! 🐾"
            )
            
        # Resolve user directory shortcut (~)
        resolved_path = os.path.abspath(os.path.expanduser(raw_path))
        
        if not os.path.exists(resolved_path):
            event_bus.publish("FILE_READ_FAILED", file_path=raw_path, error="File not found")
            return CapabilityResult(
                success=False,
                data={"error": "File not found", "path": resolved_path},
                message=f"Meow... I couldn't find the file at `{raw_path}`! 🐾"
            )
            
        if not os.path.isfile(resolved_path):
            return CapabilityResult(
                success=False,
                data={"error": "Not a file", "path": resolved_path},
                message=f"Meow... `{raw_path}` is a directory, not a file! 🐾"
            )
            
        try:
            # Read file (limit to first 2000 chars to avoid memory issues and giant outputs)
            file_size = os.path.getsize(resolved_path)
            
            with open(resolved_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(2000)
                
            truncated = file_size > 2000
            filename = os.path.basename(resolved_path)
            
            message = mochi_voice.format_file_reader(filename, content, truncated)
            
            # Fire event
            event_bus.publish("FILE_READ", file_path=resolved_path, file_size=file_size, truncated=truncated)
            
            return CapabilityResult(
                success=True,
                data={
                    "file_path": resolved_path,
                    "filename": filename,
                    "file_size": file_size,
                    "truncated": truncated,
                    "content": content
                },
                message=message
            )
        except Exception as e:
            event_bus.publish("FILE_READ_FAILED", file_path=resolved_path, error=str(e))
            return CapabilityResult(
                success=False,
                data={"error": str(e), "path": resolved_path},
                message=f"Meow... I got an error trying to read `{raw_path}`: {e} 🐾"
            )
