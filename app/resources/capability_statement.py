from typing import Dict, Any
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from datetime import datetime
from fhir.resources.capabilitystatement import CapabilityStatement
from fhir.resources.bundle import Bundle
from fhir.resources.meta import Meta

from ..utils import FHIRJSONResponse, fhir_error_handler

router = APIRouter()

def create_capability_statement() -> CapabilityStatement:
    """
    Create a FHIR capability statement for the server.
    """
    capability = CapabilityStatement.model_construct(
        status="active",
        date=datetime.now().strftime("%Y-%m-%d"),
        kind="instance",
        software={
            "name": "FHIR Facade",
            "version": "1.0.0",
        },
        implementation={
            "description": "FHIR Facade API",
            "url": "/fhir"
        },
        fhirVersion="4.0.1",
        format=["json"],
        rest=[{
            "mode": "server",
            "resource": [
                {
                    "type": "Patient",
                    "profile": "http://hl7.org/fhir/StructureDefinition/Patient",
                    "interaction": [
                        {"code": "read"},
                        {"code": "search-type"},
                        {"code": "create"}
                    ],
                    "searchParam": [
                        {"name": "family", "type": "string", "documentation": "Search by family name (case-insensitive, partial match)"},
                        {"name": "given", "type": "string", "documentation": "Search by given name (case-insensitive, partial match)"},
                        {"name": "birthdate", "type": "date", "documentation": "Search by birth date (YYYY, YYYY-MM, or YYYY-MM-DD)"}
                    ]
                },
                {
                    "type": "Observation",
                    "profile": "http://hl7.org/fhir/StructureDefinition/Observation",
                    "interaction": [
                        {"code": "read"},
                        {"code": "search-type"}
                    ],
                    "searchParam": [
                        {"name": "patient", "type": "reference", "documentation": "Search by patient reference"},
                        {"name": "code", "type": "token", "documentation": "Search by observation code"},
                        {"name": "date", "type": "date", "documentation": "Search by observation date"}
                    ]
                }
            ]
        }]
    )
    return capability

@router.get("/metadata", summary="Capability Statement", tags=["Capability Statement"])
async def capability_statement():
    """Get the capability statement for this FHIR server."""
    capability = create_capability_statement()
    return FHIRJSONResponse(content=capability.model_dump(exclude_none=True), status_code=status.HTTP_200_OK, media_type="application/fhir+json")

