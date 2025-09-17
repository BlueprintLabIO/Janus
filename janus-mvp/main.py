import asyncio
import uvicorn

from janus_mvp.server.api import create_app


def main():
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()

