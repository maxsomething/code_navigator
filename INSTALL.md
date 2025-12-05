Installation Guide for Code_Navigator

This guide covers setting up the environment for Arch Linux, Debian/Ubuntu, and Fedora.

Code_Navigator relies on Qt6 for the GUI, Ollama for the AI backend, and C-compilers to build the language parsers (Tree-sitter).

1. Install System Dependencies
Arch Linux (Recommended)

Arch is the primary development target. Dependencies are available directly in pacman.


# 1. Update system
sudo pacman -Syu

# 2. Install Python, Build Tools (for Tree-sitter), Git, and Qt6
sudo pacman -S python python-pip git base-devel qt6-base qt6-webengine

# 3. Install Ollama
sudo pacman -S ollama
Debian / Ubuntu (22.04+)

Ubuntu often separates development headers required to build Python extensions.


# 1. Update repositories
sudo apt update

# 2. Install Python, Pip, Venv, Git, and Build Essentials (GCC/Make for Tree-sitter)
sudo apt install python3 python3-venv python3-pip git build-essential python3-dev

# 3. Install Qt6 System Libraries (Ensures PyQt6-WebEngine runs smoothly)
sudo apt install libqt6core6a libqt6gui6 libqt6widgets6 libqt6webenginecore6-bin libgl1-mesa-glx

# 4. Install Ollama (Using the official script as it's rarely in apt)
curl -fsSL https://ollama.com/install.sh | sh
Fedora

Fedora users need the development tools and Qt6 packages.


# 1. Install Python, Dev Tools, and Qt6
sudo dnf install python3 python3-pip python3-devel git gcc gcc-c++ qt6-qtbase qt6-qtwebengine

# 2. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
2. Set Up the Python Environment

Code_Navigator should be run inside a virtual environment to avoid conflicting with system packages.

Clone the Repository (if you haven't already):


git clone https://github.com/yourusername/code_navigator.git
cd code_navigator

Create the Virtual Environment:


python3 -m venv .venv

Activate the Environment:


source .venv/bin/activate

Upgrade pip (Important for installing binary wheels):


pip install --upgrade pip

Install Dependencies:
This will compile the Tree-sitter bindings. Ensure you installed base-devel, build-essential, or gcc in Step 1.


pip install -r requirements.txt
3. Configure AI Service (Ollama)

Start the Service:

Arch/Fedora (Systemd):


sudo systemctl enable --now ollama

Ubuntu (if installed via script):
It usually starts automatically. If not, run ollama serve in a separate terminal.

Download the Model:
The default configuration uses mistral.


ollama pull mistral
4. Run the Application

With the virtual environment active (source .venv/bin/activate) and Ollama running:


python main.py
Troubleshooting

Tree-sitter installation fails:

Error: command 'gcc' failed or Python.h: No such file.

Fix: You are missing C++ compilers or Python headers. Re-run the "Install System Dependencies" step for your distro (specifically base-devel, build-essential, or python3-devel).

Qt/GUI fails to launch:

Error: xcb plugin missing or shared library errors.

Fix: Ensure you have the system Qt6 packages installed. On Ubuntu, you may also need sudo apt install libxcb-cursor0.

Ollama Connection Error:

Error: HTTPConnectionPool ... Connection refused.

Fix: Ensure Ollama is running (systemctl status ollama or check if localhost:11434 is active).