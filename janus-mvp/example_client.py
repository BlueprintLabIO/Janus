import asyncio
import sys
import httpx


BASE_URL = "http://localhost:8000"


async def send(message: str, user_id: str = "test_user", session_id: str = "test_session"):
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            f"{BASE_URL}/chat",
            json={"message": message, "user_id": user_id, "session_id": session_id},
        )
        r.raise_for_status()
        print(r.json())


async def interactive():
    print("Interactive mode. Type messages, Ctrl+C to exit.")
    while True:
        try:
            msg = input(">> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break
        if not msg:
            continue
        await send(msg)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        asyncio.run(interactive())
    else:
        asyncio.run(send("Hello Janus!"))


if __name__ == "__main__":
    main()

