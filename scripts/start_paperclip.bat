@echo off
set PATH=C:\Users\Titouza\Documents\AI corpo\ai-agent-company\tools\node-v20.18.3-win-x64;%PATH%
cd /d "C:\Users\Titouza\Documents\AI corpo\ai-agent-company\vendor\paperclip"
echo Node version:
node --version
echo Starting Paperclip...
npx pnpm dev
