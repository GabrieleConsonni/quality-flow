import os

from fastapi import APIRouter

router = APIRouter(prefix="/public")


@router.get("/idp-config")
def get_idp_config():
    issuer_uri = os.getenv("IDP_ISSUER_URI", "https://akeron-keycloak.akeroncloud.com")
    return {"issuerUri": issuer_uri}
