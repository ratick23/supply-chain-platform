from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from logger import StructuredLoggingMiddleware
from routers import health, shipments, routes, data_quality #, predictions

app = FastAPI(
    title="Supply Chain Intelligence Mini-Platform API",
    version="1.0.0",
    description="Serving Layer API for shipments, route metrics, DQ reporting, and delay predictions."
)

# 1. Register structured logging middleware
app.add_middleware(StructuredLoggingMiddleware)

# 2. Register global exception handler for unexpected 500s
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "InternalServerError", "detail": str(exc)}
    )

# 3. Mount routers
app.include_router(health.router)
app.include_router(shipments.router)
app.include_router(routes.router)
app.include_router(data_quality.router)
#app.include_router(predictions.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)