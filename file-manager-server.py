#!/usr/bin/env python3
"""
MCP Server for File Management
Provides file and directory operations with safety controls
"""

import json
import sys
import os
import shutil
import glob
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, List, Any, Optional
import base64

class MCPFileServer:
    def __init__(self):
        self.tools = {
            "read_file": {
                "description": "Read contents of a file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file to read"
                        },
                        "encoding": {
                            "type": "string",
                            "description": "File encoding",
                            "default": "utf-8"
                        }
                    },
                    "required": ["path"]
                }
            },
            "write_file": {
                "description": "Write content to a file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file to write"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file"
                        },
                        "encoding": {
                            "type": "string",
                            "description": "File encoding",
                            "default": "utf-8"
                        },
                        "append": {
                            "type": "boolean",
                            "description": "Append to file instead of overwriting",
                            "default": False
                        }
                    },
                    "required": ["path", "content"]
                }
            },
            "list_files": {
                "description": "List files in a directory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Directory path",
                            "default": "."
                        },
                        "pattern": {
                            "type": "string",
                            "description": "Glob pattern for filtering",
                            "default": "*"
                        },
                        "recursive": {
                            "type": "boolean",
                            "description": "Search recursively",
                            "default": False
                        }
                    }
                }
            },
            "create_directory": {
                "description": "Create a directory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Directory path to create"
                        },
                        "parents": {
                            "type": "boolean",
                            "description": "Create parent directories if needed",
                            "default": True
                        }
                    },
                    "required": ["path"]
                }
            },
            "delete_file": {
                "description": "Delete a file or directory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to delete"
                        },
                        "recursive": {
                            "type": "boolean",
                            "description": "Delete directories recursively",
                            "default": False
                        }
                    },
                    "required": ["path"]
                }
            },
            "move_file": {
                "description": "Move or rename a file or directory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "description": "Source path"
                        },
                        "destination": {
                            "type": "string",
                            "description": "Destination path"
                        }
                    },
                    "required": ["source", "destination"]
                }
            },
            "copy_file": {
                "description": "Copy a file or directory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "description": "Source path"
                        },
                        "destination": {
                            "type": "string",
                            "description": "Destination path"
                        },
                        "recursive": {
                            "type": "boolean",
                            "description": "Copy directories recursively",
                            "default": False
                        }
                    },
                    "required": ["source", "destination"]
                }
            },
            "get_file_info": {
                "description": "Get detailed information about a file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path"
                        }
                    },
                    "required": ["path"]
                }
            },
            "search_files": {
                "description": "Search for files containing specific text",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "Directory to search in",
                            "default": "."
                        },
                        "pattern": {
                            "type": "string",
                            "description": "Text pattern to search for"
                        },
                        "file_pattern": {
                            "type": "string",
                            "description": "File pattern to search in",
                            "default": "*"
                        }
                    },
                    "required": ["pattern"]
                }
            }
        }
        
        # Set safe working directory
        self.safe_root = os.path.expanduser("~")
    
    def is_safe_path(self, file_path: str) -> bool:
        """Check if path is safe to access"""
        try:
            # Resolve to absolute path
            abs_path = os.path.abspath(os.path.expanduser(file_path))
            # Check if it's within safe boundaries
            return not abs_path.startswith(('/etc', '/sys', '/proc', 'C:\\Windows', 'C:\\Program Files'))
        except:
            return False
    
    def handle_initialize(self, request: Dict) -> Dict:
        """Handle initialization request"""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {}
            },
            "serverInfo": {
                "name": "file-manager",
                "version": "1.0.0"
            }
        }
    
    def handle_list_tools(self, request: Dict) -> Dict:
        """List available tools"""
        tools_list = []
        for name, tool in self.tools.items():
            tools_list.append({
                "name": name,
                "description": tool["description"],
                "inputSchema": tool["inputSchema"]
            })
        return {"tools": tools_list}
    
    def handle_call_tool(self, request: Dict) -> Dict:
        """Execute a tool"""
        tool_name = request.get("params", {}).get("name")
        arguments = request.get("params", {}).get("arguments", {})
        
        tool_handlers = {
            "read_file": self.read_file,
            "write_file": self.write_file,
            "list_files": self.list_files,
            "create_directory": self.create_directory,
            "delete_file": self.delete_file,
            "move_file": self.move_file,
            "copy_file": self.copy_file,
            "get_file_info": self.get_file_info,
            "search_files": self.search_files
        }
        
        handler = tool_handlers.get(tool_name)
        if handler:
            return handler(arguments)
        else:
            return {
                "error": {
                    "code": -32601,
                    "message": f"Unknown tool: {tool_name}"
                }
            }
    
    def read_file(self, args: Dict) -> Dict:
        """Read file contents"""
        file_path = args.get("path", "")
        encoding = args.get("encoding", "utf-8")
        
        if not self.is_safe_path(file_path):
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: Access to this path is restricted"
                }]
            }
        
        try:
            # Check if file is binary
            mime_type, _ = mimetypes.guess_type(file_path)
            
            if mime_type and mime_type.startswith(('image/', 'audio/', 'video/', 'application/octet-stream')):
                # Read as binary and encode to base64
                with open(file_path, 'rb') as f:
                    content = base64.b64encode(f.read()).decode('ascii')
                return {
                    "content": [{
                        "type": "text",
                        "text": f"Binary file (base64 encoded):\n{content}"
                    }]
                }
            else:
                # Read as text
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                return {
                    "content": [{
                        "type": "text",
                        "text": content
                    }]
                }
        except Exception as e:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error reading file: {str(e)}"
                }]
            }
    
    def write_file(self, args: Dict) -> Dict:
        """Write content to file"""
        file_path = args.get("path", "")
        content = args.get("content", "")
        encoding = args.get("encoding", "utf-8")
        append = args.get("append", False)
        
        if not self.is_safe_path(file_path):
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: Access to this path is restricted"
                }]
            }
        
        try:
            mode = 'a' if append else 'w'
            with open(file_path, mode, encoding=encoding) as f:
                f.write(content)
            
            action = "appended to" if append else "written to"
            return {
                "content": [{
                    "type": "text",
                    "text": f"Successfully {action} file: {file_path}"
                }]
            }
        except Exception as e:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error writing file: {str(e)}"
                }]
            }
    
    def list_files(self, args: Dict) -> Dict:
        """List files in directory"""
        directory = args.get("path", ".")
        pattern = args.get("pattern", "*")
        recursive = args.get("recursive", False)
        
        if not self.is_safe_path(directory):
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: Access to this path is restricted"
                }]
            }
        
        try:
            if recursive:
                search_pattern = os.path.join(directory, "**", pattern)
                files = glob.glob(search_pattern, recursive=True)
            else:
                search_pattern = os.path.join(directory, pattern)
                files = glob.glob(search_pattern)
            
            # Get file details
            file_list = []
            for file_path in files:
                if os.path.exists(file_path):
                    stat = os.stat(file_path)
                    file_list.append({
                        "path": file_path,
                        "type": "dir" if os.path.isdir(file_path) else "file",
                        "size": stat.st_size,
                        "modified": stat.st_mtime
                    })
            
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps(file_list, indent=2)
                }]
            }
        except Exception as e:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error listing files: {str(e)}"
                }]
            }
    
    def create_directory(self, args: Dict) -> Dict:
        """Create directory"""
        dir_path = args.get("path", "")
        parents = args.get("parents", True)
        
        if not self.is_safe_path(dir_path):
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: Access to this path is restricted"
                }]
            }
        
        try:
            Path(dir_path).mkdir(parents=parents, exist_ok=True)
            return {
                "content": [{
                    "type": "text",
                    "text": f"Successfully created directory: {dir_path}"
                }]
            }
        except Exception as e:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error creating directory: {str(e)}"
                }]
            }
    
    def delete_file(self, args: Dict) -> Dict:
        """Delete file or directory"""
        file_path = args.get("path", "")
        recursive = args.get("recursive", False)
        
        if not self.is_safe_path(file_path):
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: Access to this path is restricted"
                }]
            }
        
        try:
            if os.path.isdir(file_path):
                if recursive:
                    shutil.rmtree(file_path)
                else:
                    os.rmdir(file_path)
            else:
                os.remove(file_path)
            
            return {
                "content": [{
                    "type": "text",
                    "text": f"Successfully deleted: {file_path}"
                }]
            }
        except Exception as e:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error deleting file: {str(e)}"
                }]
            }
    
    def move_file(self, args: Dict) -> Dict:
        """Move or rename file"""
        source = args.get("source", "")
        destination = args.get("destination", "")
        
        if not self.is_safe_path(source) or not self.is_safe_path(destination):
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: Access to this path is restricted"
                }]
            }
        
        try:
            shutil.move(source, destination)
            return {
                "content": [{
                    "type": "text",
                    "text": f"Successfully moved {source} to {destination}"
                }]
            }
        except Exception as e:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error moving file: {str(e)}"
                }]
            }
    
    def copy_file(self, args: Dict) -> Dict:
        """Copy file or directory"""
        source = args.get("source", "")
        destination = args.get("destination", "")
        recursive = args.get("recursive", False)
        
        if not self.is_safe_path(source) or not self.is_safe_path(destination):
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: Access to this path is restricted"
                }]
            }
        
        try:
            if os.path.isdir(source):
                if recursive:
                    shutil.copytree(source, destination)
                else:
                    return {
                        "content": [{
                            "type": "text",
                            "text": "Error: Use recursive=true to copy directories"
                        }]
                    }
            else:
                shutil.copy2(source, destination)
            
            return {
                "content": [{
                    "type": "text",
                    "text": f"Successfully copied {source} to {destination}"
                }]
            }
        except Exception as e:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error copying file: {str(e)}"
                }]
            }
    
    def get_file_info(self, args: Dict) -> Dict:
        """Get detailed file information"""
        file_path = args.get("path", "")
        
        if not self.is_safe_path(file_path):
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: Access to this path is restricted"
                }]
            }
        
        try:
            if not os.path.exists(file_path):
                return {
                    "content": [{
                        "type": "text",
                        "text": f"File not found: {file_path}"
                    }]
                }
            
            stat = os.stat(file_path)
            path_obj = Path(file_path)
            
            info = {
                "path": file_path,
                "absolute_path": str(path_obj.absolute()),
                "type": "directory" if os.path.isdir(file_path) else "file",
                "size": stat.st_size,
                "size_readable": self._human_readable_size(stat.st_size),
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
                "accessed": stat.st_atime,
                "permissions": oct(stat.st_mode)[-3:],
                "owner": stat.st_uid,
                "group": stat.st_gid
            }
            
            if os.path.isfile(file_path):
                # Add file-specific info
                mime_type, _ = mimetypes.guess_type(file_path)
                info["mime_type"] = mime_type
                
                # Calculate hash for small files
                if stat.st_size < 100 * 1024 * 1024:  # 100MB limit
                    with open(file_path, 'rb') as f:
                        info["md5"] = hashlib.md5(f.read()).hexdigest()
            
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps(info, indent=2)
                }]
            }
        except Exception as e:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error getting file info: {str(e)}"
                }]
            }
    
    def search_files(self, args: Dict) -> Dict:
        """Search for files containing text"""
        directory = args.get("directory", ".")
        search_pattern = args.get("pattern", "")
        file_pattern = args.get("file_pattern", "*")
        
        if not self.is_safe_path(directory):
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: Access to this path is restricted"
                }]
            }
        
        try:
            results = []
            search_path = os.path.join(directory, "**", file_pattern)
            
            for file_path in glob.glob(search_path, recursive=True):
                if os.path.isfile(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if search_pattern.lower() in content.lower():
                                # Find line numbers
                                lines = content.split('\n')
                                matching_lines = []
                                for i, line in enumerate(lines, 1):
                                    if search_pattern.lower() in line.lower():
                                        matching_lines.append({
                                            "line_number": i,
                                            "content": line.strip()[:100]  # First 100 chars
                                        })
                                
                                results.append({
                                    "file": file_path,
                                    "matches": matching_lines[:5]  # Limit to first 5 matches
                                })
                    except:
                        # Skip files that can't be read as text
                        pass
            
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps(results, indent=2) if results else "No matches found"
                }]
            }
        except Exception as e:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error searching files: {str(e)}"
                }]
            }
    
    def _human_readable_size(self, size: int) -> str:
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"
    
    def handle_request(self, request: Dict) -> Dict:
        """Main request handler"""
        method = request.get("method")
        
        handlers = {
            "initialize": self.handle_initialize,
            "tools/list": self.handle_list_tools,
            "tools/call": self.handle_call_tool,
        }
        
        handler = handlers.get(method)
        if handler:
            try:
                result = handler(request)
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": result
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                }
        else:
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    def run(self):
        """Run the MCP server"""
        while True:
            try:
                # Read from stdin
                line = sys.stdin.readline()
                if not line:
                    break
                
                # Parse JSON-RPC request
                request = json.loads(line)
                
                # Handle request
                response = self.handle_request(request)
                
                # Write response to stdout
                print(json.dumps(response))
                sys.stdout.flush()
                
            except json.JSONDecodeError as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}"
                    }
                }
                print(json.dumps(error_response))
                sys.stdout.flush()
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
                print(json.dumps(error_response))
                sys.stdout.flush()

if __name__ == "__main__":
    server = MCPFileServer()
    server.run()