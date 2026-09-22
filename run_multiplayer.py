"""Run the live listening game. Launch from the project root on macOS/Windows."""

import argparse

import uvicorn


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    print(f"Open http://127.0.0.1:{args.port} in your browser.")
    if args.host == "0.0.0.0":
        print("For phones on the same Wi-Fi, use this computer's LAN IP instead of 127.0.0.1.")
    uvicorn.run("multiplayer.server:app", host=args.host, port=args.port, workers=1)
