from fastapi import FastAPI
from src.api.routes import router
import uvicorn

app = FastAPI(title="OData Query Converter")

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)