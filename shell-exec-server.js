#!/usr/bin/env node
/**
 * MCP Server for Shell Command Execution
 * Allows execution of shell commands with safety controls
 */

const readline = require('readline');
const { exec, spawn } = require('child_process');
const path = require('path');
const os = require('os');

class MCPShellServer {
    constructor() {
        this.tools = {
            execute_command: {
                description: "Execute a shell command",
                inputSchema: {
                    type: "object",
                    properties: {
                        command: {
                            type: "string",
                            description: "Shell command to execute"
                        },
                        cwd: {
                            type: "string",
                            description: "Working directory for command execution",
                            default: process.cwd()
                        },
                        timeout: {
                            type: "integer",
                            description: "Command timeout in milliseconds",
                            default: 30000
                        }
                    },
                    required: ["command"]
                }
            },
            list_directory: {
                description: "List contents of a directory",
                inputSchema: {
                    type: "object",
                    properties: {
                        path: {
                            type: "string",
                            description: "Directory path to list",
                            default: "."
                        }
                    }
                }
            },
            get_system_info: {
                description: "Get system information",
                inputSchema: {
                    type: "object",
                    properties: {}
                }
            },
            set_environment: {
                description: "Set an environment variable for subsequent commands",
                inputSchema: {
                    type: "object",
                    properties: {
                        name: {
                            type: "string",
                            description: "Environment variable name"
                        },
                        value: {
                            type: "string",
                            description: "Environment variable value"
                        }
                    },
                    required: ["name", "value"]
                }
            }
        };
        
        // Environment variables for command execution
        this.customEnv = { ...process.env };
        
        // Setup readline interface for stdin/stdout
        this.rl = readline.createInterface({
            input: process.stdin,
            output: process.stdout,
            terminal: false
        });
    }
    
    handleInitialize(request) {
        return {
            protocolVersion: "2024-11-05",
            capabilities: {
                tools: {},
                resources: {}
            },
            serverInfo: {
                name: "shell-exec",
                version: "1.0.0"
            }
        };
    }
    
    handleListTools(request) {
        const tools = Object.entries(this.tools).map(([name, tool]) => ({
            name,
            description: tool.description,
            inputSchema: tool.inputSchema
        }));
        
        return { tools };
    }
    
    async handleCallTool(request) {
        const toolName = request.params?.name;
        const args = request.params?.arguments || {};
        
        switch (toolName) {
            case 'execute_command':
                return await this.executeCommand(args);
            case 'list_directory':
                return await this.listDirectory(args);
            case 'get_system_info':
                return this.getSystemInfo(args);
            case 'set_environment':
                return this.setEnvironment(args);
            default:
                throw new Error(`Unknown tool: ${toolName}`);
        }
    }
    
    executeCommand(args) {
        return new Promise((resolve) => {
            const { command, cwd = process.cwd(), timeout = 30000 } = args;
            
            // Security check - block obviously dangerous commands
            const dangerousPatterns = [
                /rm\s+-rf\s+\//,
                /format\s+[cC]:/,
                /del\s+\/[sS]/,
                />\/dev\/sda/
            ];
            
            if (dangerousPatterns.some(pattern => pattern.test(command))) {
                resolve({
                    content: [{
                        type: "text",
                        text: "Error: Command blocked for safety reasons"
                    }]
                });
                return;
            }
            
            exec(command, {
                cwd,
                timeout,
                env: this.customEnv,
                maxBuffer: 1024 * 1024 * 10 // 10MB buffer
            }, (error, stdout, stderr) => {
                if (error) {
                    resolve({
                        content: [{
                            type: "text",
                            text: `Command failed:\n${error.message}\n${stderr}`
                        }]
                    });
                } else {
                    let output = stdout;
                    if (stderr) {
                        output += `\nStderr:\n${stderr}`;
                    }
                    resolve({
                        content: [{
                            type: "text",
                            text: output || "Command executed successfully with no output"
                        }]
                    });
                }
            });
        });
    }
    
    listDirectory(args) {
        return new Promise((resolve) => {
            const dirPath = args.path || '.';
            const command = process.platform === 'win32' 
                ? `dir "${dirPath}"` 
                : `ls -la "${dirPath}"`;
            
            exec(command, (error, stdout, stderr) => {
                if (error) {
                    resolve({
                        content: [{
                            type: "text",
                            text: `Error listing directory: ${error.message}`
                        }]
                    });
                } else {
                    resolve({
                        content: [{
                            type: "text",
                            text: stdout
                        }]
                    });
                }
            });
        });
    }
    
    getSystemInfo(args) {
        const info = {
            platform: os.platform(),
            release: os.release(),
            type: os.type(),
            arch: os.arch(),
            hostname: os.hostname(),
            cpus: os.cpus().length,
            totalMemory: `${Math.round(os.totalmem() / (1024 * 1024 * 1024))} GB`,
            freeMemory: `${Math.round(os.freemem() / (1024 * 1024 * 1024))} GB`,
            homeDir: os.homedir(),
            tempDir: os.tmpdir(),
            uptime: `${Math.round(os.uptime() / 3600)} hours`,
            nodeVersion: process.version,
            cwd: process.cwd()
        };
        
        return {
            content: [{
                type: "text",
                text: JSON.stringify(info, null, 2)
            }]
        };
    }
    
    setEnvironment(args) {
        const { name, value } = args;
        this.customEnv[name] = value;
        
        return {
            content: [{
                type: "text",
                text: `Environment variable ${name} set to: ${value}`
            }]
        };
    }
    
    handleRequest(request) {
        const method = request.method;
        
        const handlers = {
            'initialize': () => this.handleInitialize(request),
            'tools/list': () => this.handleListTools(request),
            'tools/call': () => this.handleCallTool(request)
        };
        
        const handler = handlers[method];
        if (!handler) {
            throw new Error(`Method not found: ${method}`);
        }
        
        return handler();
    }
    
    async processRequest(line) {
        try {
            const request = JSON.parse(line);
            const result = await this.handleRequest(request);
            
            const response = {
                jsonrpc: "2.0",
                id: request.id,
                result
            };
            
            console.log(JSON.stringify(response));
        } catch (error) {
            const errorResponse = {
                jsonrpc: "2.0",
                id: null,
                error: {
                    code: -32603,
                    message: error.message
                }
            };
            console.log(JSON.stringify(errorResponse));
        }
    }
    
    run() {
        this.rl.on('line', (line) => {
            if (line.trim()) {
                this.processRequest(line);
            }
        });
        
        this.rl.on('close', () => {
            process.exit(0);
        });
    }
}

// Start the server
const server = new MCPShellServer();
server.run();
