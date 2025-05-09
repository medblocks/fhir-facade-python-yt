# CRUD & search logic -> Observation FHIR 
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Request, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fhir.resources.observation import Observation
from fhir.resources.bundle import Bundle, BundleEntry
from datetime import datetime, date, timezone
from fhir.resources.reference import Reference

from ..db import get_db
from ..models import BloodPressureModel, HeartRateModel, PatientModel # Import PatientModel for joins/filtering
from ..utils import FHIRJSONResponse, fhir_error_handler

router = APIRouter()

# Refactored to_bundle
def to_bundle(resources: List[Observation], type_: str = "searchset") -> Bundle:
    """Creates a FHIR Bundle from a list of FHIR resource Pydantic models."""
    serialized_resources = [r.model_dump(exclude_none=True) for r in resources]
    return Bundle.model_construct(
        type=type_,
        total=len(resources),
        entry=[BundleEntry.model_construct(resource=r) for r in serialized_resources]
    )

# --- Conversion Functions ---

def bp_to_observation(bp: BloodPressureModel) -> Observation:
    """Convert BloodPressureModel to FHIR Observation."""
    # Convert date to datetime for FHIR
    # effective_datetime = datetime.combine(bp.date, datetime.min.time()) # This was naive
    
    return Observation(
        id=f"bp-{bp.id}",
        status="final",
        code={
            "coding": [{
                "system": "http://loinc.org",
                "code": "85354-9",
                "display": "Blood pressure panel"
            }]
        },
        subject=Reference(reference=f"Patient/{bp.patient_id}"),
        effectiveDateTime=bp.date.isoformat(), # Use YYYY-MM-DD format
        component=[
            {
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "8480-6",
                        "display": "Systolic blood pressure"
                    }]
                },
                "valueQuantity": {
                    "value": float(bp.systolic),
                    "unit": "mmHg",
                    "system": "http://unitsofmeasure.org",
                    "code": "mm[Hg]"
                }
            },
            {
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "8462-4",
                        "display": "Diastolic blood pressure"
                    }]
                },
                "valueQuantity": {
                    "value": float(bp.diastolic),
                    "unit": "mmHg",
                    "system": "http://unitsofmeasure.org",
                    "code": "mm[Hg]"
                }
            }
        ]
    )

def hr_to_observation(hr: HeartRateModel) -> Observation:
    """Convert HeartRateModel to FHIR Observation."""
    
    # effectiveDateTime should be the date from hr.date as YYYY-MM-DD
    # Since hr.date is now a Date object, its isoformat() is already correct.
    effective_fhir_date = hr.date.isoformat()
        
    return Observation(
        id=f"hr-{hr.id}",
        status="final",
        code={
            "coding": [{
                "system": "http://loinc.org",
                "code": "8867-4",
                "display": "Heart rate"
            }]
        },
        subject=Reference(reference=f"Patient/{hr.patient_id}"),
        effectiveDateTime=effective_fhir_date, # Use the YYYY-MM-DD date string
        valueQuantity={
            "value": float(hr.rate), # Changed from hr.heart_rate to hr.rate
            "unit": "beats/minute",
            "system": "http://unitsofmeasure.org",
            "code": "/min"
        }
    )

# --- API Endpoints ---

@router.get("/Observation/{observation_id}", response_model=Observation, summary="Read Observation", tags=["Observation"])
async def read_observation(
    observation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Read a single observation by ID."""
    if observation_id.startswith("bp-"):
        # Blood pressure observation
        try:
            bp_id = int(observation_id[3:])
        except ValueError:
            return fhir_error_handler(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid observation ID format", 
                diagnostic=f"Expected numeric ID after 'bp-' prefix, received: {observation_id[3:]}"
            )
            
        result = await db.execute(
            select(BloodPressureModel).where(BloodPressureModel.id == bp_id)
        )
        bp = result.scalar_one_or_none()
        if not bp:
            return fhir_error_handler(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blood pressure observation not found",
                diagnostic=f"No blood pressure observation with ID {bp_id} exists"
            )
        observation = bp_to_observation(bp)
        return FHIRJSONResponse(content=observation.model_dump(exclude_none=True), status_code=200, media_type="application/fhir+json")
    elif observation_id.startswith("hr-"):
        # Heart rate observation
        try:
            hr_id = int(observation_id[3:])
        except ValueError:
            return fhir_error_handler(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid observation ID format",
                diagnostic=f"Expected numeric ID after 'hr-' prefix, received: {observation_id[3:]}"
            )
            
        result = await db.execute(
            select(HeartRateModel).where(HeartRateModel.id == hr_id)
        )
        hr = result.scalar_one_or_none()
        if not hr:
            return fhir_error_handler(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Heart rate observation not found",
                diagnostic=f"No heart rate observation with ID {hr_id} exists"
            )
        observation = hr_to_observation(hr)
        return FHIRJSONResponse(content=observation.model_dump(exclude_none=True), status_code=200, media_type="application/fhir+json")
    else:
        return fhir_error_handler(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid observation ID format",
            diagnostic=f"Observation ID must start with 'bp-' or 'hr-', received: {observation_id}"
        )

@router.get("/Observation", response_model=Bundle, summary="Search Observations", tags=["Observation"])
async def search_observations(
    request: Request,
    patient: Optional[str] = Query(None, description="Patient reference (e.g., 'Patient/123')"),
    code: Optional[str] = Query(None, description="Observation code (e.g., '8867-4' for heart rate)"),
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db)
):
    """Search observations with various filters."""
    all_observation_models: List[Observation] = [] # Changed from entries to a list of Observation models
    
    # Parse date if provided
    search_date = None
    if date:
        try:
            search_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            return fhir_error_handler(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format",
                diagnostic=f"Date must be in YYYY-MM-DD format, received: {date}"
            )

    # Parse patient ID if provided
    patient_id = None
    if patient:
        if not patient.startswith("Patient/"):
            return fhir_error_handler(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid patient reference format",
                diagnostic="Patient reference must be in the format 'Patient/{id}'"
            )
        try:
            patient_id = int(patient.split("/")[1])
        except (IndexError, ValueError):
            return fhir_error_handler(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid patient ID",
                diagnostic=f"Expected numeric patient ID, received: {patient}"
            )

    # Search blood pressure observations
    bp_query = select(BloodPressureModel)
    if patient_id:
        bp_query = bp_query.where(BloodPressureModel.patient_id == patient_id)
    if search_date:
        bp_query = bp_query.where(BloodPressureModel.date == search_date)
    if code and code != "85354-9":  # Skip if code doesn't match blood pressure panel
        bp_query = None # Explicitly set to None

    if bp_query is not None: # Changed from `if bp_query:`
        result = await db.execute(bp_query)
        for bp in result.scalars():
            observation = bp_to_observation(bp)
            all_observation_models.append(observation) # Add model to list

    # Search heart rate observations
    hr_query = select(HeartRateModel)
    if patient_id:
        hr_query = hr_query.where(HeartRateModel.patient_id == patient_id)
    if search_date:
        hr_query = hr_query.where(HeartRateModel.date == search_date)
    if code and code != "8867-4":  # Skip if code doesn't match heart rate
        hr_query = None # Explicitly set to None

    if hr_query is not None: # Changed from `if hr_query:`
        result = await db.execute(hr_query)
        for hr in result.scalars():
            observation = hr_to_observation(hr)
            all_observation_models.append(observation) # Add model to list

    bundle = to_bundle(all_observation_models)
    return FHIRJSONResponse(content=bundle.model_dump(exclude_none=True), status_code=200, media_type="application/fhir+json") 