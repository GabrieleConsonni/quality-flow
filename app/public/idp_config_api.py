import os

from fastapi import APIRouter

router = APIRouter(prefix="/public")


@router.get("/idp-config")
def get_idp_config():
    issuer_uri = os.getenv("IDP_ISSUER_URI", "http://localhost:8180")
    return {"issuerUri": issuer_uri}
