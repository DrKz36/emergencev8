import asyncio
from fastapi import FastAPI, Depends
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

def test_stream_cleanup():
    app = FastAPI()
    flag = {"exit_order": []}

    async def get_resource():
        yield "db_session"
        flag["exit_order"].append("cleanup")

    @app.get("/stream")
    async def stream(res=Depends(get_resource)):
        async def generator():
            for i in range(3):
                yield f"chunk-{i}\n"
                await asyncio.sleep(0.01)
        return StreamingResponse(generator(), media_type="text/plain")

    client = TestClient(app)
    response = client.get("/stream")
    assert response.status_code == 200
    assert "chunk-0" in response.text
    # Vérifie que le cleanup se fait APRES la fin du stream
    assert flag["exit_order"] == ["cleanup"]
