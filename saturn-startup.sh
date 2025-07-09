#!/bin/bash

# Saturn Cloud H100 Startup Script for Trae AI Chat Assistant
# This script sets up the environment and starts the FastAPI server

set -e  # Exit on any error

echo "🚀 Starting Trae AI Chat Assistant on Saturn Cloud H100..."

# Set environment variables
export PYTHONPATH="/home/jovyan/work:$PYTHONPATH"
export TRANSFORMERS_CACHE="/home/jovyan/work/models"
export HF_HOME="/home/jovyan/work/models"
export CUDA_VISIBLE_DEVICES=0

# Create necessary directories
mkdir -p /home/jovyan/work/models
mkdir -p /home/jovyan/work/logs

# Navigate to project directory
cd /home/jovyan/work

echo "📦 Installing Python dependencies..."
# Install requirements
pip install --upgrade pip
pip install -r server/requirements.txt

# Install additional dependencies for H100 optimization
pip install flash-attn --no-build-isolation
pip install xformers

echo "🔧 Configuring GPU settings..."
# Check GPU availability
nvidia-smi

# Set optimal GPU settings for H100
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
export CUDA_LAUNCH_BLOCKING=0

echo "📥 Pre-downloading model (this may take a few minutes)..."
# Pre-download the model to avoid timeout during first request
python3 -c "
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import os

print('Setting up model configuration...')
model_name = 'unsloth/gemma-2-9b-it-bnb-4bit'

# Configure quantization for memory efficiency
quant_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type='nf4',
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True
)

print(f'Downloading tokenizer for {model_name}...')
tokenizer = AutoTokenizer.from_pretrained(
    model_name,
    cache_dir=os.environ.get('TRANSFORMERS_CACHE', './models')
)

print(f'Downloading model {model_name}...')
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    quantization_config=quant_config,
    device_map='auto',
    torch_dtype=torch.float16,
    cache_dir=os.environ.get('TRANSFORMERS_CACHE', './models')
)

print('✅ Model downloaded and cached successfully!')
print(f'Model device: {model.device}')
print(f'Model dtype: {model.dtype}')
"

echo "🌐 Starting FastAPI server..."
# Start the server with optimized settings for production
cd server
uvicorn app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --loop uvloop \
    --http httptools \
    --access-log \
    --log-level info \
    --timeout-keep-alive 30 \
    --timeout-graceful-shutdown 10 &

# Store the server PID
SERVER_PID=$!
echo "Server started with PID: $SERVER_PID"

# Wait a moment for server to start
sleep 5

# Check if server is running
if ps -p $SERVER_PID > /dev/null; then
    echo "✅ Server is running successfully!"
    echo "🔗 Access the chat interface at: http://localhost:8000"
    echo "📊 API documentation at: http://localhost:8000/docs"
    echo "💡 Health check at: http://localhost:8000/health"
else
    echo "❌ Server failed to start. Check logs for details."
    exit 1
fi

# Function to handle shutdown
shutdown() {
    echo "🛑 Shutting down server..."
    kill $SERVER_PID
    wait $SERVER_PID
    echo "✅ Server stopped gracefully"
    exit 0
}

# Trap signals for graceful shutdown
trap shutdown SIGTERM SIGINT

# Keep the script running and monitor the server
while true; do
    if ! ps -p $SERVER_PID > /dev/null; then
        echo "❌ Server process died unexpectedly. Restarting..."
        cd /home/jovyan/work/server
        uvicorn app:app \
            --host 0.0.0.0 \
            --port 8000 \
            --workers 1 \
            --loop uvloop \
            --http httptools \
            --access-log \
            --log-level info \
            --timeout-keep-alive 30 \
            --timeout-graceful-shutdown 10 &
        SERVER_PID=$!
        echo "Server restarted with PID: $SERVER_PID"
    fi
    sleep 10
done