import os
from app import app

if __name__ == "__main__":
    # Use PORT environment variable for platform flexibility (Heroku, Koyeb, etc.)
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
