# Installing and Starting Docker

This guide provides instructions for installing and starting Docker on both macOS and Windows systems.

- [Installing and Starting Docker](#installing-and-starting-docker)
  - [System Requirements](#system-requirements)
    - [macOS](#macos)
    - [Windows](#windows)
  - [Installation](#installation)
    - [macOS Installation](#macos-installation)
    - [Windows Installation](#windows-installation)
  - [Starting Docker](#starting-docker)
  - [Troubleshooting](#troubleshooting)
    - [Common Issues on macOS](#common-issues-on-macos)
    - [Common Issues on Windows](#common-issues-on-windows)

## System Requirements

### macOS

- macOS version 10.15 or newer
- At least 4GB RAM
- VirtualizationFramework enabled ([docs](https://github.com/docker/enable-macos-virtualization-framework))

### Windows

- Windows 10/11 Pro, Enterprise, or Education (64-bit)
- WSL 2 enabled
- 4GB RAM minimum
- BIOS-level hardware virtualization support ([docs](https://support.microsoft.com/en-us/windows/enable-virtualization-on-windows-c5578302-6e43-4b4b-a449-8ced115f58e1))

## Installation

### macOS Installation

1. Visit the [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop) website
2. Click "Download for Mac"
3. Choose the appropriate version:
   - For Apple Silicon (M1/M2) Macs: Download Apple Chip version
   - For Intel Macs: Download Intel Chip version
4. Double-click the downloaded `Docker.dmg` file
5. Drag the Docker app to your Applications folder
6. Open Docker from Applications folder
7. Follow the prompts to grant necessary permissions

### Windows Installation

1. Enable Windows Subsystem for Linux (WSL 2):
   - Open PowerShell as Administrator
   - Run: `wsl --install`
   - Restart your computer

2. Visit the [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop) website
3. Click "Download for Windows"
4. Run the downloaded `Docker Desktop Installer.exe`
5. Follow the installation wizard
6. Ensure "Use WSL 2 instead of Hyper-V" is selected
7. Click "OK" to complete installation
8. Restart your computer

## Starting Docker

1. Open Docker Desktop from Applications folder or menu bar
2. Wait for the Docker engine to start (whale icon in menu bar)
3. Open Terminal to verify installation:

```bash
docker --version
docker run hello-world
```

## Troubleshooting

### Common Issues on macOS

- If Docker fails to start, check System Preferences → Security & Privacy for blocked permissions ([docs](https://docs.docker.com/desktop/settings/mac/#security))
- Ensure you have adequate disk space (minimum 20GB recommended) ([docs](https://docs.docker.com/desktop/install/mac-install/#system-requirements))
- For M1/M2 Macs, ensure Rosetta 2 is installed if using Intel-based containers ([docs](https://support.apple.com/en-us/HT211861))

### Common Issues on Windows

- Ensure WSL 2 is properly installed and set as default ([docs](https://learn.microsoft.com/en-us/windows/wsl/install))
- Check that virtualization is enabled in BIOS ([docs](https://docs.docker.com/desktop/troubleshoot/topics/#virtualization))
- Verify Windows 10/11 is updated to latest version ([docs](https://docs.docker.com/desktop/install/windows-install/#system-requirements))
- Ensure Hyper-V feature is enabled (Windows Pro/Enterprise/Education editions) ([docs](https://docs.docker.com/desktop/troubleshoot/topics/#hyper-v))
