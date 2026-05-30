import pytest
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from httpx import ASGITransport, AsyncClient

from app.middleware.error_handler import ErrorHandlerMiddleware, http_exception_handler


def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_exception_handler(FastAPIHTTPException, http_exception_handler)

    @app.get("/ok")
    async def ok_endpoint() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/http-error")
    async def http_error_endpoint() -> None:
        raise HTTPException(status_code=404, detail="Resource not found")

    @app.get("/unhandled-error")
    async def unhandled_error_endpoint() -> None:
        raise RuntimeError("Something went wrong")

    return app


@pytest.fixture
async def test_client():
    app = _create_test_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


async def test_unhandled_exception_returns_500(test_client: AsyncClient) -> None:
    response = await test_client.get("/unhandled-error")

    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "Internal Server Error"
    assert "message" in body
    assert "request_id" in body


async def test_http_exception_returns_proper_status(test_client: AsyncClient) -> None:
    response = await test_client.get("/http-error")

    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "Not Found"
    assert body["message"] == "Resource not found"
    assert "request_id" in body


async def test_request_id_is_uuid(test_client: AsyncClient) -> None:
    response = await test_client.get("/unhandled-error")
    body = response.json()
    request_id = body["request_id"]

    parts = request_id.split("-")
    assert len(parts) == 5
    assert len(parts[0]) == 8
    assert len(parts[1]) == 4
    assert len(parts[2]) == 4
    assert len(parts[3]) == 4
    assert len(parts[4]) == 12


async def test_success_response_unaffected(test_client: AsyncClient) -> None:
    response = await test_client.get("/ok")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
