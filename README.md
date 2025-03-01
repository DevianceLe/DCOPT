# DCOPT - Deviance's Cursor Ollama Proxy Thingy

A powerful proxy server that connects Cursor IDE to your local Ollama instance, enabling seamless integration with local LLMs.

## Features

- 🤖 Interactive model selection
- 🔄 Automatic model pulling
- 🌐 SSH tunneling support
- 🚇 Ngrok integration
- 🎨 Colorized console output
- 💻 Cross-platform compatibility
- 🔌 OpenAI API compatibility layer

## Prerequisites

- Python 3.7+
- [Ollama](https://ollama.ai) installed and accessible
- [Cursor IDE](https://cursor.sh)
- (Optional) [ngrok](https://ngrok.com) for public access
- (Optional) SSH access for remote tunneling

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
python ollama_for_cursor.py
```

This will:
1. Start a proxy server on port 11435
2. Let you select a model interactively
3. Connect to your local Ollama instance

### Command Line Options

```bash
python ollama_for_cursor.py --help
```

Available options:
- `--port PORT`: Set proxy port (default: 11435)
- `--model MODEL`: Specify model name
- `--start-ollama`: Start Ollama if not running
- `--debug`: Enable debug logging

### SSH Tunneling

To use SSH tunneling:
```bash
python ollama_for_cursor.py --use-ssh --ssh-host your.server.com --ssh-user username
```

SSH options:
- `--ssh-host`: SSH host to connect to
- `--ssh-port`: SSH port (default: 22)
- `--ssh-user`: SSH username
- `--ssh-password`: SSH password
- `--ssh-key-file`: SSH private key file
- `--ssh-remote-port`: Remote port to forward to

### Ngrok Integration

To expose your proxy through ngrok:
```bash
python ollama_for_cursor.py --use-ngrok
```

## Cursor IDE Configuration

1. Open Cursor Settings (Ctrl + ,)
2. Go to Models tab
3. Set 'Override OpenAI Base URL' to your proxy URL
4. Set 'OpenAI API Key' to 'ollama'
5. Set 'Override chat model' to your chosen model
6. Save and test with a chat message

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

- Deviance (https://github.com/deviancele) 