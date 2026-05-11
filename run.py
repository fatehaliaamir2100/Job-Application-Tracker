"""Main entry point with background scheduler."""
import uvicorn
from backend.app.main import app
from backend.app.scheduler import scheduler
from backend.app.config import settings


if __name__ == "__main__":
    print("=" * 60)
    print("🎯 Job Application Tracker")
    print("=" * 60)
    print()
    print(f"🌐 Starting server on http://{settings.host}:{settings.port}")
    print(f"🔄 Auto-sync enabled (every {settings.sync_interval_minutes} minutes)")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()
    
    try:
        # Start background scheduler
        scheduler.start()
        
        # Start FastAPI server
        uvicorn.run(
            app,
            host=settings.host,
            port=settings.port,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
        scheduler.stop()
        print("✅ Goodbye!")
