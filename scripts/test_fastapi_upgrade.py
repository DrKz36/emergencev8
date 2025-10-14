#!/usr/bin/env python3
"""
Test script to validate FastAPI 0.119 compatibility with EmergenceV8.

Critical areas to test:
1. Dependency injection with yield (cleanup timing)
2. StreamingResponse with dependencies
3. WebSocket endpoints with Depends
4. Pydantic v2 compatibility
5. Background tasks behavior

Usage:
    python scripts/test_fastapi_upgrade.py
"""
import asyncio
import logging
import sys
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, List

# Add src to path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SRC_DIR = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class FastAPIUpgradeTests:
    """Test suite for FastAPI 0.119 upgrade compatibility."""

    def __init__(self):
        self.results: List[Dict[str, Any]] = []

    def test_result(self, name: str, passed: bool, details: str = ""):
        """Record test result."""
        self.results.append({
            "test": name,
            "passed": passed,
            "details": details,
        })
        status = "✓" if passed else "✗"
        logger.info(f"{status} {name}: {details}")

    async def test_dependency_yield_cleanup(self):
        """Test that dependencies with yield cleanup after response."""
        from fastapi import FastAPI, Depends
        from fastapi.responses import StreamingResponse
        from fastapi.testclient import TestClient

        test_name = "Dependency yield cleanup timing"

        try:
            app = FastAPI()
            cleanup_log: List[str] = []

            async def test_dependency():
                """Dependency that tracks cleanup timing."""
                cleanup_log.append("entered")
                yield "resource"
                cleanup_log.append("cleanup")

            @app.get("/test-stream")
            async def stream_endpoint(dep=Depends(test_dependency)):
                async def generate():
                    for i in range(3):
                        yield f"chunk-{i}\n"
                        await asyncio.sleep(0.001)
                    cleanup_log.append("stream_done")
                return StreamingResponse(generate(), media_type="text/plain")

            client = TestClient(app)
            response = client.get("/test-stream")

            # Verify response success
            assert response.status_code == 200
            assert "chunk-0" in response.text
            assert "chunk-2" in response.text

            # Verify cleanup order (critical for FastAPI 0.109 vs 0.119)
            # In 0.109: cleanup happens AFTER stream completes
            # In 0.119: behavior should be consistent but needs verification
            expected_order = ["entered", "stream_done", "cleanup"]

            if cleanup_log == expected_order:
                self.test_result(
                    test_name,
                    True,
                    f"Cleanup order correct: {cleanup_log}"
                )
            else:
                self.test_result(
                    test_name,
                    False,
                    f"Cleanup order unexpected. Expected {expected_order}, got {cleanup_log}"
                )

        except Exception as e:
            self.test_result(test_name, False, f"Exception: {e}")

    async def test_streaming_response_no_interruption(self):
        """Test that streaming responses aren't interrupted by cleanup."""
        from fastapi import FastAPI, Depends
        from fastapi.responses import StreamingResponse
        from fastapi.testclient import TestClient

        test_name = "StreamingResponse not interrupted by cleanup"

        try:
            app = FastAPI()
            chunks_sent: List[int] = []

            async def db_session():
                """Simulated DB session dependency."""
                yield "session"
                # Cleanup should not interrupt stream

            @app.get("/stream")
            async def stream(session=Depends(db_session)):
                async def generate():
                    for i in range(10):
                        chunks_sent.append(i)
                        yield f"data-{i}\n"
                        await asyncio.sleep(0.001)
                return StreamingResponse(generate(), media_type="text/plain")

            client = TestClient(app)
            response = client.get("/stream")

            # Verify all chunks were sent
            assert response.status_code == 200
            assert len(chunks_sent) == 10
            for i in range(10):
                assert f"data-{i}" in response.text

            self.test_result(
                test_name,
                True,
                f"All {len(chunks_sent)} chunks sent successfully"
            )

        except Exception as e:
            self.test_result(test_name, False, f"Exception: {e}")

    async def test_pydantic_v2_models(self):
        """Test Pydantic v2 model compatibility."""
        test_name = "Pydantic v2 model compatibility"

        try:
            from pydantic import BaseModel, Field, ConfigDict
            from fastapi import FastAPI
            from fastapi.testclient import TestClient

            # Test Pydantic v2 model
            class TestModel(BaseModel):
                model_config = ConfigDict(strict=True)

                user_id: str = Field(..., min_length=1)
                data: Dict[str, Any] = Field(default_factory=dict)

            app = FastAPI()

            @app.post("/test-pydantic")
            async def test_endpoint(model: TestModel):
                return {"received": model.model_dump()}

            client = TestClient(app)
            response = client.post(
                "/test-pydantic",
                json={"user_id": "test123", "data": {"key": "value"}}
            )

            assert response.status_code == 200
            assert response.json()["received"]["user_id"] == "test123"

            self.test_result(
                test_name,
                True,
                "Pydantic v2 models work correctly"
            )

        except Exception as e:
            self.test_result(test_name, False, f"Exception: {e}")

    async def test_websocket_with_depends(self):
        """Test WebSocket endpoints with Depends."""
        test_name = "WebSocket with Depends compatibility"

        try:
            from fastapi import FastAPI, Depends, WebSocket
            from fastapi.testclient import TestClient

            app = FastAPI()

            async def get_ws_dependency():
                """WebSocket dependency."""
                yield "ws_resource"

            @app.websocket("/ws-test")
            async def websocket_endpoint(websocket: WebSocket, dep=Depends(get_ws_dependency)):
                await websocket.accept()
                await websocket.send_text("connected")
                data = await websocket.receive_text()
                await websocket.send_text(f"echo: {data}")
                await websocket.close()

            client = TestClient(app)
            with client.websocket_connect("/ws-test") as websocket:
                data = websocket.receive_text()
                assert data == "connected"
                websocket.send_text("hello")
                response = websocket.receive_text()
                assert response == "echo: hello"

            self.test_result(
                test_name,
                True,
                "WebSocket with Depends works correctly"
            )

        except Exception as e:
            self.test_result(test_name, False, f"Exception: {e}")

    async def test_background_tasks(self):
        """Test BackgroundTasks behavior."""
        test_name = "BackgroundTasks execution"

        try:
            from fastapi import FastAPI, BackgroundTasks
            from fastapi.testclient import TestClient

            app = FastAPI()
            task_executed: List[bool] = []

            def background_task(name: str):
                task_executed.append(True)

            @app.get("/with-task")
            async def endpoint_with_task(background_tasks: BackgroundTasks):
                background_tasks.add_task(background_task, "test")
                return {"status": "ok"}

            client = TestClient(app)
            response = client.get("/with-task")

            assert response.status_code == 200
            # BackgroundTasks should execute after response
            await asyncio.sleep(0.1)  # Give time for task to execute
            assert len(task_executed) > 0

            self.test_result(
                test_name,
                True,
                "BackgroundTasks executed successfully"
            )

        except Exception as e:
            self.test_result(test_name, False, f"Exception: {e}")

    async def test_lifespan_context_manager(self):
        """Test lifespan context manager (FastAPI 0.109+)."""
        test_name = "Lifespan context manager"

        try:
            from fastapi import FastAPI
            from contextlib import asynccontextmanager

            startup_log: List[str] = []

            @asynccontextmanager
            async def lifespan(app: FastAPI):
                # Startup
                startup_log.append("startup")
                yield
                # Shutdown
                startup_log.append("shutdown")

            app = FastAPI(lifespan=lifespan)

            @app.get("/test")
            async def test_endpoint():
                return {"status": "ok"}

            # TestClient triggers lifespan
            from fastapi.testclient import TestClient
            with TestClient(app) as client:
                response = client.get("/test")
                assert response.status_code == 200

            # Verify lifespan events
            assert "startup" in startup_log
            assert "shutdown" in startup_log

            self.test_result(
                test_name,
                True,
                f"Lifespan events: {startup_log}"
            )

        except Exception as e:
            self.test_result(test_name, False, f"Exception: {e}")

    async def run_all(self):
        """Run all tests."""
        logger.info("="*60)
        logger.info("Starting FastAPI 0.119 upgrade compatibility tests")
        logger.info("="*60)

        await self.test_dependency_yield_cleanup()
        await self.test_streaming_response_no_interruption()
        await self.test_pydantic_v2_models()
        await self.test_websocket_with_depends()
        await self.test_background_tasks()
        await self.test_lifespan_context_manager()

        logger.info("="*60)
        logger.info("Test suite completed")
        logger.info("="*60)

    def print_summary(self):
        """Print test summary."""
        passed = sum(1 for r in self.results if r["passed"])
        total = len(self.results)

        print("\n" + "="*60)
        print("TEST RESULTS SUMMARY")
        print("="*60)

        for result in self.results:
            status = "✓ PASS" if result["passed"] else "✗ FAIL"
            print(f"{status}: {result['test']}")
            if result["details"]:
                print(f"       {result['details']}")

        print("\n" + "-"*60)
        print(f"TOTAL: {passed}/{total} tests passed")
        print("="*60)

        return passed == total


async def main():
    """Main test runner."""
    try:
        tests = FastAPIUpgradeTests()
        await tests.run_all()
        all_passed = tests.print_summary()

        if all_passed:
            logger.info("✅ All tests passed - FastAPI 0.119 upgrade compatible")
            sys.exit(0)
        else:
            logger.warning("⚠️  Some tests failed - review before upgrading")
            sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
