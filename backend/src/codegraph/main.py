from fastapi import FastAPI

app = FastAPI(title="CodeGraph Agent")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
