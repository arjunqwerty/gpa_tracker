"""FastAPI application. Run with:  uvicorn app.main:app --reload  (from the backend folder)."""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from pymongo.errors import DuplicateKeyError, OperationFailure

from app import database
from app.ownership import get_current_user
from app.routers import auth, calculations, configuration, courses, exports, imports, profile, results, semesters
from app.seed import seed_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    await seed_database()
    yield
    await database.disconnect()


app = FastAPI(title="VIT CGPA Tracker", lifespan=lifespan)

app.include_router(auth.router)
# Everything else needs a logged-in user, including the shared reference data.
for module in (profile, configuration, semesters, courses, results, calculations, imports, exports):
    app.include_router(module.router, dependencies=[Depends(get_current_user)])


@app.exception_handler(DuplicateKeyError)
async def duplicate_key(request, exc):
    return JSONResponse(status_code=409, content={"detail": "Something with the same email, code or attempt number already exists. Change that value and try again."})


@app.exception_handler(OperationFailure)
async def write_conflict(request, exc):
    """Two requests changed the same documents inside transactions at the same moment."""
    if not exc.has_error_label("TransientTransactionError"):
        raise exc
    return JSONResponse(status_code=409, content={"detail": "This was changed by another request at the same moment. Reload and try again."})
