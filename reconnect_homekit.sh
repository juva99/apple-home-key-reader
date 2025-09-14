#!/bin/bash

# HomeKit Reconnection Tool for Linux/macOS
# This script provides easy access to common reconnection tasks

echo ""
echo "==============================================="
echo "   Apple Home Key Reader - HomeKit Reconnection"
echo "==============================================="
echo ""

show_menu() {
    echo "Choose an option:"
    echo ""
    echo "1. Check Status"
    echo "2. Show QR Code"
    echo "3. Restart Service"
    echo "4. Reset Pairing (WARNING: Removes all pairings)"
    echo "5. Check Configuration"
    echo "6. Exit"
    echo ""
}

while true; do
    show_menu
    read -p "Enter your choice (1-6): " choice
    
    case $choice in
        1)
            echo ""
            echo "Checking status..."
            python3 reconnect_homekit.py --check-status
            echo ""
            read -p "Press Enter to continue..."
            ;;
        2)
            echo ""
            echo "Displaying QR code..."
            python3 reconnect_homekit.py --show-qr
            echo ""
            read -p "Press Enter to continue..."
            ;;
        3)
            echo ""
            echo "Restarting HomeKit service..."
            echo "Press Ctrl+C to stop the service when ready."
            python3 reconnect_homekit.py --restart-service
            echo ""
            read -p "Press Enter to continue..."
            ;;
        4)
            echo ""
            echo "WARNING: This will remove ALL HomeKit pairings!"
            read -p "Are you sure? (y/N): " confirm
            if [[ $confirm =~ ^[Yy]$ ]]; then
                python3 reconnect_homekit.py --reset-pairing
            else
                echo "Operation cancelled."
            fi
            echo ""
            read -p "Press Enter to continue..."
            ;;
        5)
            echo ""
            echo "Checking configuration..."
            python3 reconnect_homekit.py --repair-config
            echo ""
            read -p "Press Enter to continue..."
            ;;
        6)
            echo ""
            echo "Goodbye!"
            exit 0
            ;;
        *)
            echo "Invalid choice. Please try again."
            ;;
    esac
done
