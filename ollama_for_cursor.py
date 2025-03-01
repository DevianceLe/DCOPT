#!/usr/bin/env python3
"""
DCOPT - Deviance's Cursor Ollama Proxy Thingy

A powerful proxy server that connects Cursor IDE to your local Ollama instance.
Features:
- Interactive model selection
- SSH tunneling support
- Ngrok integration
- Colorized console output
- Automatic model pulling
- Cross-platform compatibility

Author: Deviance
License: MIT
"""

import http.server
import socketserver
import urllib.request
import urllib.error
import json
import sys
import time
import logging
import argparse
import os
import subprocess
import re
import colorama

# Configure logging with cleaner output and colors
colorama.init()

# Color constants
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('dcopt')

# Configuration
CONFIG = {
    "ollama_url": "http://127.0.0.1:11434",  # Ollama URL
    "proxy_port": 11435,                    # Proxy port
    "model_name": "deepseek-r1:7b",         # Default model
    "retry_count": 3,                       # Retries for failed requests
    "retry_delay": 0.5,                     # Delay between retries
    "use_ngrok": False,                     # Enable ngrok (disabled by default)
    "ngrok_authtoken": "",                  # Your ngrok auth token
    "request_timeout": 300,                 # Request timeout in seconds (5 minutes)
    "max_buffer_size": 1024 * 1024 * 1000, # 50MB buffer for large responses
    "chunk_size": 16384,                   # 16KB chunks for streaming
    "max_retries_on_timeout": 2,           # Additional retries on timeout
    "use_ssh": False,                      # Enable SSH tunneling
    "ssh_host": "",                        # SSH host to connect to
    "ssh_port": 22,                        # SSH port
    "ssh_user": "",                        # SSH username
    "ssh_password": "",                    # SSH password
    "ssh_key_file": "",                    # SSH private key file (optional)
    "ssh_remote_port": 11435,              # Remote port to forward to (same as proxy_port)
}


class CORSProxyHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler with CORS, streaming, and console logging"""

    def log_request(self, code='-', size='-'):
        """Override to provide minimal request logging"""
        if self.path not in ['/', '/v1', '/favicon.ico']:  # Skip logging for common endpoints
            logger.debug(f"Request: {self.command} {self.path} {code}")

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        """Handle GET requests"""
        logger.info(f"\n=== GET Request to {self.path} ===")
        
        # Handle root endpoint
        if self.path == "/" or self.path == "/v1":
            self.send_response(200)
            self.send_cors_headers()
            self.send_header('Content-Type', 'application/json')
            response = {
                "status": "ok",
                "version": "v1",
                "message": "Ollama proxy is running"
            }
            response_json = json.dumps(response)
            self.send_header('Content-Length', str(len(response_json.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(response_json.encode('utf-8'))
            self.wfile.flush()
            return
            
        # Handle models endpoint
        elif self.path == '/v1/models':
            try:
                result = subprocess.run(["ollama", "list"], capture_output=True, text=True, shell=True)
                logger.info(f"Ollama list output: {result.stdout}")
                models = []
                if result.returncode == 0:
                    for line in result.stdout.splitlines()[1:]:  # Skip header
                        if line.strip():
                            model_name = line.split()[0]
                            models.append({
                                "id": model_name,
                                "object": "model",
                                "created": int(time.time()),
                                "owned_by": "ollama"
                            })
                
                response = {
                    "object": "list",
                    "data": models
                }
                
                response_json = json.dumps(response)
                logger.info(f"Sending response: {response_json}")
                
                self.send_response(200)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(response_json.encode('utf-8'))))
                self.end_headers()
                
                self.wfile.write(response_json.encode('utf-8'))
                self.wfile.flush()
            except Exception as e:
                logger.error(f"Error getting model list: {e}")
                error_response = {
                    "error": {
                        "message": f"Failed to get model list: {str(e)}",
                        "type": "server_error",
                        "code": 500
                    }
                }
                error_json = json.dumps(error_response)
                self.send_response(500)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(error_json.encode('utf-8'))))
                self.end_headers()
                self.wfile.write(error_json.encode('utf-8'))
                self.wfile.flush()
            return
        
        # Handle favicon.ico
        elif self.path == '/favicon.ico':
            self.send_response(204)  # No content
            self.end_headers()
            return
            
        # All other endpoints
        else:
            logger.info(f"Unhandled GET path: {self.path}")
            error_response = {
                "error": {
                    "message": f"Endpoint not found: {self.path}",
                    "type": "not_found",
                    "code": 404
                }
            }
            error_json = json.dumps(error_response)
            self.send_response(404)
            self.send_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(error_json.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(error_json.encode('utf-8'))
            self.wfile.flush()

    def do_POST(self):
        """Handle POST requests"""
        logger.info("\n=== Cursor POST Request ===")
        logger.info(f"Path: {self.path}")
        logger.info(f"Headers: {dict(self.headers)}")
        self.proxy_request("POST")

    def send_cors_headers(self):
        """Add CORS headers"""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS, GET")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def proxy_request(self, method):
        """Proxy request to Ollama with streaming support"""
        target_url = CONFIG["ollama_url"] + "/api/generate" if self.path in ['/chat/completions', '/v1/chat/completions'] else CONFIG["ollama_url"] + self.path

        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else None

            if method == 'POST' and body:
                try:
                    body_json = json.loads(body)
                    logger.info("\n=== Request Body ===")
                    logger.info(json.dumps(body_json, indent=2))
                    logger.info("===================")

                    if self.path in ['/chat/completions', '/v1/chat/completions']:
                        messages = body_json.get("messages", [])
                        stream = body_json.get("stream", False)
                        
                        # Convert GPT model names to default model
                        requested_model = body_json.get("model", CONFIG["model_name"])
                        if requested_model.startswith(("gpt-3", "gpt-4")):
                            model = CONFIG["model_name"]
                            logger.info(f"Converting {requested_model} to {model}")
                        else:
                            model = requested_model
                        
                        prompt_parts = []
                        for msg in messages:
                            content = msg.get('content', '')
                            role = msg.get('role', '')
                            if role == "system":
                                prompt_parts.append(f"[INST]<<SYS>>{content}<</SYS>>[/INST]")
                            elif role == "user":
                                prompt_parts.append(f"[INST]{content}[/INST]")
                            else:
                                prompt_parts.append(content)
                        
                        ollama_request = {
                            "model": model,
                            "prompt": "\n".join(prompt_parts),
                            "stream": stream,
                            "options": {
                                "temperature": body_json.get("temperature", 0.7),
                                "top_p": body_json.get("top_p", 1.0),
                                "num_predict": body_json.get("max_tokens", 4096),
                                "stop": body_json.get("stop", ["[INST]", "</s>"]) if isinstance(body_json.get("stop"), list) else ["[INST]", "</s>"]
                            }
                        }
                        logger.info("\n=== Transformed Request ===")
                        logger.info(json.dumps(ollama_request, indent=2))
                        logger.info("========================")
                        body = json.dumps(ollama_request).encode('utf-8')
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in request: {e}")
                    error_response = {
                        "error": {
                            "message": f"Invalid JSON in request: {str(e)}",
                            "type": "invalid_request_error",
                            "code": 400
                        }
                    }
                    self.send_response(400)
                    self.send_cors_headers()
                    self.send_header('Content-Type', 'application/json')
                    error_json = json.dumps(error_response)
                    self.send_header('Content-Length', str(len(error_json.encode('utf-8'))))
                    self.end_headers()
                    self.wfile.write(error_json.encode('utf-8'))
                    return

            headers = {'Content-Type': 'application/json'}
            request = urllib.request.Request(target_url, data=body, headers=headers, method=method)
            
            with urllib.request.urlopen(request, timeout=CONFIG["request_timeout"]) as response:
                if self.path in ['/chat/completions', '/v1/chat/completions'] and body_json.get("stream", False):
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/event-stream')
                    self.send_header('Cache-Control', 'no-cache')
                    self.send_cors_headers()
                    self.end_headers()

                    completion_id = f"chatcmpl-{int(time.time())}"
                    created = int(time.time())
                    model = body_json.get("model", CONFIG["model_name"])
                    
                    # Send initial role
                    initial_chunk = {
                        'id': completion_id,
                        'object': 'chat.completion.chunk',
                        'created': created,
                        'model': model,
                        'choices': [{'index': 0, 'delta': {'role': 'assistant'}, 'finish_reason': None}]
                    }
                    logger.info("\n=== Initial Chunk ===")
                    logger.info(json.dumps(initial_chunk, indent=2))
                    logger.info("===================")
                    self.wfile.write(f"data: {json.dumps(initial_chunk)}\n\n".encode('utf-8'))
                    self.wfile.flush()

                    buffer = ""
                    while True:
                        chunk = response.read(CONFIG["chunk_size"]).decode('utf-8')
                        if not chunk:
                            break
                        buffer += chunk
                        
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            if line.strip():
                                try:
                                    data = json.loads(line)
                                    if 'response' in data:
                                        event_data = {
                                            'id': completion_id,
                                            'object': 'chat.completion.chunk',
                                            'created': created,
                                            'model': model,
                                            'choices': [{'index': 0, 'delta': {'content': data['response']}, 'finish_reason': None}]
                                        }
                                        logger.info(f"Streaming chunk: {data['response']}")
                                        self.wfile.write(f"data: {json.dumps(event_data)}\n\n".encode('utf-8'))
                                        self.wfile.flush()
                                    if data.get('done'):
                                        final_chunk = {
                                            'id': completion_id,
                                            'object': 'chat.completion.chunk',
                                            'created': created,
                                            'model': model,
                                            'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]
                                        }
                                        logger.info("\n=== Final Chunk ===")
                                        logger.info(json.dumps(final_chunk, indent=2))
                                        logger.info("==================")
                                        self.wfile.write(f"data: {json.dumps(final_chunk)}\n\n".encode('utf-8'))
                                        self.wfile.write(b"data: [DONE]\n\n")
                                        self.wfile.flush()
                                        return
                                except json.JSONDecodeError:
                                    continue
                else:
                    response_body = response.read()
                    try:
                        ollama_response = json.loads(response_body)
                        logger.info("\n=== Ollama Response ===")
                        logger.info(json.dumps(ollama_response, indent=2))
                        logger.info("=====================")

                        response_text = ollama_response.get("response", "").strip()
                        response_text = re.sub(r'<[^>]+>', '', response_text)
                        response_text = response_text.replace("[/INST]", "").replace("[INST]", "").replace("<<SYS>>", "").replace("<</SYS>>", "").replace("</s>", "")
                        response_text = "\n".join(line.strip() for line in response_text.splitlines() if line.strip()) or "Empty response"

                        openai_response = {
                            "id": f"chat-{int(time.time())}",
                            "object": "chat.completion",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [{"index": 0, "message": {"role": "assistant", "content": response_text}, "finish_reason": "stop"}],
                            "usage": {
                                "prompt_tokens": ollama_response.get("prompt_eval_count", -1),
                                "completion_tokens": ollama_response.get("eval_count", -1),
                                "total_tokens": -1
                            }
                        }
                        logger.info("\n=== Transformed Response ===")
                        logger.info(json.dumps(openai_response, indent=2))
                        logger.info("=========================")

                        response_json = json.dumps(openai_response)
                        self.send_response(200)
                        self.send_cors_headers()
                        self.send_header('Content-Type', 'application/json')
                        self.send_header('Content-Length', str(len(response_json.encode('utf-8'))))
                        self.end_headers()
                        self.wfile.write(response_json.encode('utf-8'))
                        self.wfile.flush()
                    except json.JSONDecodeError as e:
                        logger.error(f"\n=== Error Parsing Response ===\nResponse: {response_body}\nError: {e}\n===========================")
                        error_response = {
                            "error": {
                                "message": f"Invalid response from Ollama: {str(e)}",
                                "type": "server_error",
                                "code": 500
                            }
                        }
                        error_json = json.dumps(error_response)
                        self.send_response(500)
                        self.send_cors_headers()
                        self.send_header('Content-Type', 'application/json')
                        self.send_header('Content-Length', str(len(error_json.encode('utf-8'))))
                        self.end_headers()
                        self.wfile.write(error_json.encode('utf-8'))
                        self.wfile.flush()
        except Exception as e:
            logger.error(f"\n=== Proxy Error ===\n{str(e)}\n==================")
            error_response = {
                "error": {
                    "message": f"Proxy error: {str(e)}",
                    "type": "server_error",
                    "code": 500
                }
            }
            error_json = json.dumps(error_response)
            self.send_response(500)
            self.send_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(error_json.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(error_json.encode('utf-8'))
            self.wfile.flush()


def is_ollama_running():
    """Check if Ollama is running"""
    try:
        with urllib.request.urlopen(CONFIG["ollama_url"], timeout=2):
            return True
    except Exception:
        return False


def start_ollama():
    """Start Ollama if not running"""
    if is_ollama_running():
        return True
    logger.info("Starting Ollama server...")
    try:
        process = subprocess.Popen(["ollama", "serve"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        for _ in range(10):
            time.sleep(0.5)
            if is_ollama_running():
                logger.info("✓ Ollama started successfully")
                return True
        stderr = process.stderr.read().decode()
        logger.error(f"Failed to start Ollama: {stderr}")
        return False
    except Exception as e:
        logger.error(f"Error starting Ollama: {e}")
        return False


def pull_model(model_name):
    """Pull the model if needed"""
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, shell=True)
        if model_name in result.stdout:
            logger.info(f"✓ Model {model_name} already available")
            return True
        logger.info(f"Pulling model {model_name}...")
        result = subprocess.run(["ollama", "pull", model_name], capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            logger.info(f"✓ Successfully pulled {model_name}")
            return True
        logger.error(f"Failed to pull {model_name}: {result.stderr}")
        return False
    except Exception as e:
        logger.error(f"Error pulling model: {e}")
        return False


def start_ngrok(port):
    """Start ngrok tunnel and return URL"""
    logger.info("Starting ngrok tunnel...")
    try:
        cmd = ["ngrok", "http", str(port), "--authtoken", CONFIG["ngrok_authtoken"], "--log", "stdout", "--log-format", "json"]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        start_time = time.time()
        while time.time() - start_time < 10:
            line = process.stdout.readline()
            if line:
                try:
                    log_data = json.loads(line)
                    if "url" in log_data:
                        url = log_data.get("url", '')
                        https_url = url.replace('http://', 'https://')
                        logger.info("✓ Ngrok tunnel established")
                        logger.info(f"  HTTP:  {url}")
                        logger.info(f"  HTTPS: {https_url}")
                        return url
                except json.JSONDecodeError:
                    continue

        # Fallback to ngrok API
        time.sleep(2)
        with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels") as response:
            tunnels = json.loads(response.read().decode())
            if tunnels["tunnels"]:
                return tunnels["tunnels"][0]["public_url"]

        logger.error("Failed to establish ngrok tunnel")
        return None
    except FileNotFoundError:
        logger.error("Ngrok not installed. Please install from https://ngrok.com/download")
        return None
    except Exception as e:
        logger.error(f"Ngrok error: {e}")
        return None


def start_ssh_tunnel():
    """Start SSH tunnel and return success status"""
    logger.info("Starting SSH tunnel...")
    
    try:
        if sys.platform == 'win32':
            # Use plink for Windows with proper remote forwarding
            ssh_cmd = [
                "plink",
                "-ssh",
                "-N",
                "-R", f"{CONFIG['ssh_remote_port']}:127.0.0.1:{CONFIG['proxy_port']}",
                "-P", str(CONFIG['ssh_port']),
                "-pw", CONFIG['ssh_password'],
                "-batch",  # Avoid interactive prompts
                f"{CONFIG['ssh_user']}@{CONFIG['ssh_host']}"
            ]
            logger.info("Using plink for Windows SSH connection")
        else:
            # For non-Windows systems, use traditional SSH
            ssh_cmd = [
                "ssh", "-N", 
                "-R", f"{CONFIG['ssh_remote_port']}:127.0.0.1:{CONFIG['proxy_port']}",
                "-o", "StrictHostKeyChecking=no",
                "-o", "ExitOnForwardFailure=yes",
                "-o", "GatewayPorts=yes",
                "-o", "ServerAliveInterval=60"  # Keep connection alive
            ]
            
            if CONFIG["ssh_key_file"]:
                ssh_cmd.extend(["-i", CONFIG["ssh_key_file"]])
                
            ssh_cmd.append(f"{CONFIG['ssh_user']}@{CONFIG['ssh_host']}")
        
        logger.info(f"Establishing SSH tunnel: {CONFIG['ssh_host']}:{CONFIG['ssh_remote_port']} <- Local proxy:{CONFIG['proxy_port']}")
        logger.info(f"Command: {' '.join(ssh_cmd)}")
        
        # Start SSH process
        process = subprocess.Popen(
            ssh_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False
        )
        
        # Wait a bit to check if tunnel established
        time.sleep(2)
        
        # Check if process is still running
        if process.poll() is None:
            logger.info("✓ SSH tunnel established successfully")
            logger.info(f"Your proxy is now accessible at: http://{CONFIG['ssh_host']}:{CONFIG['ssh_remote_port']}")
            logger.info("Use this URL in your Cursor settings")
            return True
        else:
            stderr = process.stderr.read().decode()
            logger.error(f"Failed to establish SSH tunnel: {stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error establishing SSH tunnel: {e}")
        return False


def list_ollama_models():
    """List available Ollama models and return them"""
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            models = []
            # Skip header line and process each model line
            for line in result.stdout.splitlines()[1:]:
                if line.strip():
                    model_name = line.split()[0]
                    models.append(model_name)
            return models
        return []
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return []


def print_header(title, subtitle=None):
    """Print a formatted header with optional subtitle"""
    logger.info(f"\n{Colors.HEADER}╔════════════════════════════════════════════════════════════╗{Colors.ENDC}")
    logger.info(f"{Colors.HEADER}║{Colors.BOLD}                                                            {Colors.ENDC}{Colors.HEADER}║{Colors.ENDC}")
    logger.info(f"{Colors.HEADER}║{Colors.BOLD}                         DCOPT                              {Colors.ENDC}{Colors.HEADER}║{Colors.ENDC}")
    logger.info(f"{Colors.HEADER}║{Colors.BOLD}                                                            {Colors.ENDC}{Colors.HEADER}║{Colors.ENDC}")
    if subtitle:
        logger.info(f"{Colors.HEADER}║{Colors.BOLD}          {subtitle.center(44)}{Colors.ENDC}{Colors.HEADER}║{Colors.ENDC}")
    logger.info(f"{Colors.HEADER}╚════════════════════════════════════════════════════════════╝{Colors.ENDC}\n")

def print_section(title):
    """Print a section title"""
    logger.info(f"\n{Colors.BLUE}{Colors.BOLD}[ {title} ]{Colors.ENDC}")

def print_success(message):
    """Print a success message"""
    logger.info(f"{Colors.GREEN}✓ {message}{Colors.ENDC}")

def print_error(message):
    """Print an error message"""
    logger.error(f"{Colors.RED}❌ {message}{Colors.ENDC}")

def print_warning(message):
    """Print a warning message"""
    logger.warning(f"{Colors.YELLOW}⚠ {message}{Colors.ENDC}")

def select_model():
    """Allow user to select a model from available ones or specify a new one"""
    available_models = list_ollama_models()
    
    if not available_models:
        print_warning("No models currently available")
        logger.info("You can pull a model using 'ollama pull <model_name>'")
        model = input(f"\n{Colors.YELLOW}Enter model name to pull (default: deepseek-r1:7b): {Colors.ENDC}").strip()
        return model if model else "deepseek-r1:7b"
    
    print_header("MODEL SELECTION")
    print_section("Available Models")
    
    for i, model in enumerate(available_models, 1):
        logger.info(f"  {Colors.BOLD}{i}.{Colors.ENDC} {model}")
    
    print_section("Options")
    logger.info(f"  {Colors.BOLD}•{Colors.ENDC} Enter a number to select an available model")
    logger.info(f"  {Colors.BOLD}•{Colors.ENDC} Enter a model name to pull a new model")
    logger.info(f"  {Colors.BOLD}•{Colors.ENDC} Press Enter to use default (deepseek-r1:7b)")
    
    choice = input(f"\n{Colors.BLUE}Your choice: {Colors.ENDC}").strip()
    
    if not choice:
        return "deepseek-r1:7b"
    
    try:
        index = int(choice) - 1
        if 0 <= index < len(available_models):
            return available_models[index]
    except ValueError:
        return choice
    
    return choice

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="DCOPT - Deviance's Cursor Ollama Proxy Thingy")
    parser.add_argument('--port', type=int, default=CONFIG["proxy_port"], help='Proxy port')
    parser.add_argument('--model', help='Model name (if not specified, will prompt to select)')
    parser.add_argument('--start-ollama', action='store_true', help='Start Ollama if not running')
    parser.add_argument('--use-ngrok', action='store_true', help='Enable ngrok tunneling (disabled by default)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    # SSH options
    ssh_group = parser.add_argument_group('SSH Tunneling')
    ssh_group.add_argument('--use-ssh', action='store_true', help='Enable SSH tunneling')
    ssh_group.add_argument('--ssh-host', help='SSH host to connect to (default: box15.millionairedesigns.com)')
    ssh_group.add_argument('--ssh-port', type=int, help='SSH port (default: 22)')
    ssh_group.add_argument('--ssh-user', help='SSH username (default: root)')
    ssh_group.add_argument('--ssh-password', help='SSH password')
    ssh_group.add_argument('--ssh-key-file', help='SSH private key file')
    ssh_group.add_argument('--ssh-remote-port', type=int, help='Remote port to forward to (default: same as proxy port)')
    
    # If no arguments provided, print help and exit
    if len(sys.argv) == 1:
        parser.print_help()
        return 0

    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    CONFIG["proxy_port"] = args.port
    CONFIG["use_ngrok"] = args.use_ngrok
    
    # Update SSH config
    if args.use_ssh:
        CONFIG["use_ssh"] = True
        if args.ssh_host is not None:
            CONFIG["ssh_host"] = args.ssh_host
        if args.ssh_port is not None:
            CONFIG["ssh_port"] = args.ssh_port
        if args.ssh_user is not None:
            CONFIG["ssh_user"] = args.ssh_user
        if args.ssh_password is not None:
            CONFIG["ssh_password"] = args.ssh_password
        if args.ssh_key_file is not None:
            CONFIG["ssh_key_file"] = args.ssh_key_file
        if args.ssh_remote_port is not None:
            CONFIG["ssh_remote_port"] = args.ssh_remote_port
        else:
            CONFIG["ssh_remote_port"] = CONFIG["proxy_port"]
    
    print_header("", "DCOPT - Deviance's Cursor Ollama Proxy Thingy     ")
    print("http://github.com/deviancele")
    
    # Check Ollama
    print_section("Checking Ollama Status")
    if not is_ollama_running():
        if args.start_ollama:
            if not start_ollama():
                print_error("Ollama setup failed. Please start it manually.")
                sys.exit(1)
        else:
            print_error("Ollama not running. Run 'ollama serve' or use --start-ollama")
            sys.exit(1)
    else:
        print_success("Ollama is running")

    # Select and pull model
    print_section("Model Setup")
    if args.model:
        CONFIG["model_name"] = args.model
        logger.info(f"Using specified model: {Colors.BOLD}{CONFIG['model_name']}{Colors.ENDC}")
    else:
        CONFIG["model_name"] = select_model()
    
    logger.info(f"\nPulling model {Colors.BOLD}{CONFIG['model_name']}{Colors.ENDC}...")
    if not pull_model(CONFIG["model_name"]):
        print_error(f"Failed to pull model {CONFIG['model_name']}")
        sys.exit(1)
    print_success(f"Model {CONFIG['model_name']} is ready")

    # Handle tunneling
    if CONFIG["use_ssh"]:
        print_section("SSH Tunnel Setup")
        if not start_ssh_tunnel():
            print_error("SSH tunnel setup failed")
            sys.exit(1)
    elif CONFIG["use_ngrok"]:
        print_section("Ngrok Tunnel Setup")
        ngrok_url = start_ngrok(CONFIG["proxy_port"])
        if not ngrok_url:
            print_warning("Ngrok setup failed, falling back to local access")

    # Start server
    try:
        server = http.server.ThreadingHTTPServer(("", CONFIG["proxy_port"]), CORSProxyHandler)
        server.allow_reuse_address = True
        print_success("Proxy server started successfully")

        # Print configuration info
        base_url = None
        if CONFIG["use_ssh"]:
            base_url = f"http://{CONFIG['ssh_host']}:{CONFIG['ssh_remote_port']}/v1"
        elif ngrok_url:
            base_url = f"{ngrok_url}/v1"
        else:
            base_url = f"http://127.0.0.1:{CONFIG['proxy_port']}/v1"

        print_section("Cursor Configuration")
        
        print_section("Connection Details")
        logger.info(f"  Base URL: {Colors.BOLD}{base_url}{Colors.ENDC}")
        logger.info(f"  API Key:  {Colors.BOLD}ollama{Colors.ENDC}")
        logger.info(f"  Model:    {Colors.BOLD}{CONFIG['model_name']}{Colors.ENDC}")
        
        if CONFIG["use_ssh"]:
            logger.info(f"\n  SSH tunnel: {Colors.BOLD}{CONFIG['ssh_host']}:{CONFIG['ssh_remote_port']} -> localhost:{CONFIG['proxy_port']}{Colors.ENDC}")
        elif ngrok_url:
            print_warning("Ngrok URL changes on restart. Update Cursor settings if needed.")
        
        print_section("Setup Steps")
        logger.info(f"  {Colors.BOLD}1.{Colors.ENDC} Open Cursor Settings (Ctrl + ,)")
        logger.info(f"  {Colors.BOLD}2.{Colors.ENDC} Go to Models tab")
        logger.info(f"  {Colors.BOLD}3.{Colors.ENDC} Set 'Override OpenAI Base URL' to the Base URL above")
        logger.info(f"  {Colors.BOLD}4.{Colors.ENDC} Set 'OpenAI API Key' to 'ollama'")
        logger.info(f"  {Colors.BOLD}5.{Colors.ENDC} Set 'Override chat model' to the Model above")
        logger.info(f"  {Colors.BOLD}6.{Colors.ENDC} Save and test with a simple chat message")
        
        print_success("Setup complete - Server is running")
        logger.info(f"\n{Colors.YELLOW}Press Ctrl+C to stop the server...{Colors.ENDC}")
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nShutting down server...")
    except Exception as e:
        logger.error(f"\nServer error: {e}")
        sys.exit(1)
    finally:
        if 'server' in locals():
            server.server_close()


if __name__ == "__main__":
    sys.exit(main())