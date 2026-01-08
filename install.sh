#!/bin/bash
# One-liner to install/update Origins Forge
echo "🚀 Updating Origins Forge..."
curl -L -o /tmp/OriginsForge.pkg https://github.com/Htet-2aung/origins-forge/releases/latest/download/OriginsForge.pkg
sudo installer -pkg /tmp/OriginsForge.pkg -target /
echo "✅ Update Complete!"
