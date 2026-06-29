from contextlib import asynccontextmanager

from fastapi import FastAPI

from connectors import scheduler
from routers import health
from routers import nginx
from routers import system
from routers import topology
from routers import oracle
from routers import peoplesoft
from routers import live
from routers import authelia_admin
from routers import admin
from routers import identity
from routers import metadata
from routers import graphdb
from routers import runtime
from routers import sqlws
from routers import ib
from routers import envcompare
from routers import tracing
from routers import record
from routers import field
from routers import role
from routers import operator

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.stop()


app = FastAPI(title="DeathStar Operations API", lifespan=lifespan)

app.include_router(health.router)
app.include_router(nginx.router)
app.include_router(system.router)
app.include_router(topology.router)
app.include_router(oracle.router)
app.include_router(peoplesoft.router)
app.include_router(live.router)
app.include_router(authelia_admin.router)
app.include_router(admin.router)
app.include_router(identity.router)
app.include_router(metadata.router)
app.include_router(graphdb.router)
app.include_router(runtime.router)
app.include_router(sqlws.router)
app.include_router(ib.router)
app.include_router(envcompare.router)
app.include_router(tracing.router)
app.include_router(record.router)
app.include_router(field.router)
app.include_router(role.router)
app.include_router(operator.router)
