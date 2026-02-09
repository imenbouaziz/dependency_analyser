#!/bin/bash
# Dependency Analyzer Streamlit UI Launcher

echo "===================================="
echo " Dependency Analyzer - Streamlit UI"
echo "===================================="
echo ""

# Check if streamlit is installed
python3 -c "import streamlit" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[ERROR] Streamlit is not installed!"
    echo ""
    echo "Installing dependencies..."
    pip3 install -r requirements.txt
    echo ""
fi

# Launch Streamlit
echo "Starting Streamlit UI..."
echo ""
echo "The app will open in your browser at:"
echo "http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

streamlit run app.py
