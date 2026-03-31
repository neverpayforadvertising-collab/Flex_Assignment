import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",   # safer import
        host="0.0.0.0",
        port=8000,
        reload=True,      # enable for debugging
        log_level="info"
    )