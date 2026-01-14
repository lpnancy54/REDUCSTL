#!/usr/bin/env python3
"""
Point d'entrée pour l'application STL Reducer SaaS.
"""

import uvicorn


def main():
    """Lance le serveur de développement."""
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["app", "templates", "static"]
    )


if __name__ == "__main__":
    main()
