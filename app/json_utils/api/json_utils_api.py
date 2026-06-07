import json

from fastapi import APIRouter
from genson import SchemaBuilder

from json_utils.models.dtos.json_payload_dto import JsonPayloadDto

router = APIRouter(prefix="/json_utils")

@router.post("/schema")
async def extract_json_schema_api(dto:JsonPayloadDto)-> dict | str:
    try:
        builder = SchemaBuilder()
        builder.add_object(dto.payload)
        schema = builder.to_schema()
        schema['title'] = str(dto.description or "payload")
        return schema
    except json.JSONDecodeError:
        return "Invalid JSON input."
