#!/usr/bin/env python3
import uvicorn

if __name__ == "__main__":
    uvicorn.run("ocp.server:app", host="0.0.0.0", port=8420, reload=False)
