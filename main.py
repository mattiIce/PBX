#!/usr/bin/env python3
"""
Main entry point for PBX system
"""
import sys
import signal
import time
from pbx.core.pbx import PBXCore

# Global running flag
running = True
pbx = None


def signal_handler(sig, frame):
    """Handle shutdown signal"""
    global running, pbx
    print("\nShutting down PBX system...")
    running = False
    if pbx:
        pbx.stop()


if __name__ == "__main__":
    print("=" * 60)
    print("InHouse PBX System v1.0.0")
    print("=" * 60)
    
    # Create PBX instance
    try:
        pbx = PBXCore("config.yml")
        
        # Register signal handler for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start PBX
        if pbx.start():
            print("\nPBX system is running...")
            print("Press Ctrl+C to stop\n")
            
            # Keep running and display status periodically
            while running:
                time.sleep(1)
                if not running:
                    break
                # Display status every 10 iterations (10 seconds)
                if int(time.time()) % 10 == 0:
                    status = pbx.get_status()
                    print(f"Status: {status['registered_extensions']} extensions registered, "
                          f"{status['active_calls']} active calls")
            
            print("PBX system shutdown complete")
        else:
            print("Failed to start PBX system")
            sys.exit(1)
            
    except FileNotFoundError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        if pbx:
            pbx.stop()
        sys.exit(1)
