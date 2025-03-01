# DCOPT - Deviance's Cursor Ollama Proxy Thingy

A powerful proxy server that connects Cursor IDE to your local Ollama instance, enabling seamless integration with local LLMs. DCOPT provides a secure and efficient bridge between Cursor's AI capabilities and your locally running Ollama models, offering features like SSH tunneling, ngrok integration, and cross-platform support.

![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

🚀 **Quick Start**: `python ollama_for_cursor.py --model deepseek-r1:7b`

💡 **Why DCOPT?**
- Run AI completions locally with your own models
- Access your Ollama instance from anywhere securely
- No need to expose your machine directly to the internet
- Works seamlessly with Cursor IDE's built-in AI features

## Features

- 🤖 Interactive model selection
- 🔄 Automatic model pulling
- 🌐 Cross-platform SSH tunneling (Paramiko + native SSH)
- 🔑 Support for password and key-based SSH authentication
- 🚇 Ngrok integration for public access
- 🎨 Colorized console output
- 💻 Cross-platform compatibility (Windows, Linux, macOS)
- 🔌 OpenAI API compatibility layer
- 🔒 Secure remote connections

## Prerequisites

- Python 3.7+
- [Ollama](https://ollama.ai) installed and accessible
- [Cursor IDE](https://cursor.sh)
- (Optional) [ngrok](https://ngrok.com) for public access
- (Optional) SSH access for remote tunneling
  - Windows: PuTTY/Plink (optional fallback)
  - Linux/macOS: OpenSSH (optional fallback)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/deviancele/dcopt.git
   cd dcopt
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage

Run the proxy with default settings:
```bash
python ollama_for_cursor.py --help
```

This will display all available options and their descriptions.

### Common Use Cases

1. Local usage:
   ```bash
   python ollama_for_cursor.py --port 11435 --model deepseek-r1:7b
   ```

2. SSH tunneling (password):
   ```bash
   python ollama_for_cursor.py --use-ssh --ssh-host your.server.com --ssh-user username --ssh-password yourpass
   ```

3. SSH tunneling (key file):
   ```bash
   python ollama_for_cursor.py --use-ssh --ssh-host your.server.com --ssh-user username --ssh-key-file ~/.ssh/id_rsa
   ```

4. Ngrok tunneling:
   ```bash
   python ollama_for_cursor.py --use-ngrok
   ```

### Command Line Options

- Basic options:
  - `--port PORT`: Set proxy port (default: 11435)
  - `--model MODEL`: Specify model name
  - `--start-ollama`: Start Ollama if not running
  - `--debug`: Enable debug logging

- SSH options:
  - `--use-ssh`: Enable SSH tunneling
  - `--ssh-host`: SSH host to connect to
  - `--ssh-port`: SSH port (default: 22)
  - `--ssh-user`: SSH username
  - `--ssh-password`: SSH password
  - `--ssh-key-file`: SSH private key file
  - `--ssh-remote-port`: Remote port to forward to

- Ngrok options:
  - `--use-ngrok`: Enable ngrok tunneling

### SSH Tunneling Details

DCOPT now uses a multi-layered approach for SSH tunneling:

1. Primary method: Paramiko (pure Python, cross-platform)
   - Supports both password and key-based authentication
   - Works consistently across all platforms
   - No external SSH tools required

2. Fallback methods:
   - Windows: Plink (from PuTTY)
   - Linux/macOS: Native SSH client

The system automatically chooses the best available method.

## Cursor IDE Configuration

1. Open Cursor Settings (Ctrl + ,)
2. Go to Models tab
3. Set 'Override OpenAI Base URL' to your proxy URL
4. Set 'OpenAI API Key' to 'ollama'
5. Set 'Override chat model' to your chosen model
6. Save and test with a chat message

## Security Notes

- SSH passwords and ngrok tokens should be provided via command line arguments
- Key-based SSH authentication is recommended over password authentication
- All connections are secured through SSH or ngrok tunneling
- Local connections are restricted to localhost by default

## Troubleshooting

1. SSH Connection Issues:
   - Ensure the SSH port is open on the remote server
   - Verify SSH credentials
   - Check if the remote port is available
   - Try key-based authentication if password auth fails

2. Model Issues:
   - Ensure Ollama is running (`ollama serve`)
   - Check if the model is downloaded (`ollama list`)
   - Try pulling the model manually (`ollama pull model_name`)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

- Deviance (https://github.com/deviancele) 