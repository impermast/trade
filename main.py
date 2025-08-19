"""
Main entry point for the Trade Project.

This module is now a simple entry point that delegates all responsibility
to the Application class for proper lifecycle management.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from CORE.application import Application


async def main():
    """
    Main application entry point.
    
    This function creates and runs the Application instance,
    which handles all the complexity of component management.
    """
    app = Application()
    
    try:
        # Initialize all components
        await app.initialize()
        
        # Run the application
        await app.run()
        
    except KeyboardInterrupt:
        print("KeyboardInterrupt received, shutting down gracefully")
    except Exception as e:
        print(f"Fatal error: {e}")
        if app.logger:
            app.logger.error(f"Fatal error in main: {e}", exc_info=True)
        else:
            import traceback
            traceback.print_exc()
    finally:
        # Ensure graceful shutdown
        if app.is_running:
            await app.shutdown()


if __name__ == "__main__":
    try:
        # Run the main application
        asyncio.run(main())
    except KeyboardInterrupt:
        print("KeyboardInterrupt received during startup")
    except Exception as e:
        print(f"Fatal error during startup: {e}")
        import traceback
        traceback.print_exc()
