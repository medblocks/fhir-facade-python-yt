# CRUD & search logic -> Observation FHIR 
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fhir.resources.observation import Observation
from fhir.resources.bundle import Bundle, BundleEntry
from datetime import datetime, date, timezone
from fhir.resources.reference import Reference

from ..db import get_db
from ..models import BloodPressureModel, HeartRateModel, PatientModel # Import PatientModel for joins/filtering

router = APIRouter()

# Added from patient.py
def remove_nulls(d: Dict[str, Any]) -> Dict[str, Any]:
    """Remove null values from a dictionary recursively and convert dates to strings."""
    if isinstance(d, date): # Handles datetime.date
        return d.isoformat()
    # Handle datetime.datetime if it appears before model_dump converts it
    if isinstance(d, datetime):
        return d.isoformat() # FHIR typically wants ISO 8601 for datetimes
    if not isinstance(d, dict):
        return d
    return {
        k: remove_nulls(v) if isinstance(v, (dict, date, datetime)) else v # Added datetime
        for k, v in d.items()
        if v is not None and (not isinstance(v, dict) or remove_nulls(v))
    }

# Refactored to_bundle
def to_bundle(resources: List[Observation], type_: str = "searchset") -> Bundle:
    """Creates a FHIR Bundle from a list of FHIR resource Pydantic models."""
    serialized_resources = [remove_nulls(r.model_dump()) for r in resources]
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
        bp_id = int(observation_id[3:])
        result = await db.execute(
            select(BloodPressureModel).where(BloodPressureModel.id == bp_id)
        )
        bp = result.scalar_one_or_none()
        if not bp:
            raise HTTPException(status_code=404, detail="Blood pressure observation not found")
        observation = bp_to_observation(bp)
        return JSONResponse(content=remove_nulls(observation.model_dump()), status_code=200, media_type="application/fhir+json")
    elif observation_id.startswith("hr-"):
        # Heart rate observation
        hr_id = int(observation_id[3:])
        result = await db.execute(
            select(HeartRateModel).where(HeartRateModel.id == hr_id)
        )
        hr = result.scalar_one_or_none()
        if not hr:
            raise HTTPException(status_code=404, detail="Heart rate observation not found")
        observation = hr_to_observation(hr)
        return JSONResponse(content=remove_nulls(observation.model_dump()), status_code=200, media_type="application/fhir+json")
    else:
        raise HTTPException(status_code=400, detail="Invalid observation ID format")

@router.get("/Observation", response_model=Bundle, summary="Search Observations", tags=["Observation"])
async def search_observations(
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
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # Parse patient ID if provided
    patient_id = None
    if patient:
        if not patient.startswith("Patient/"):
            raise HTTPException(status_code=400, detail="Invalid patient reference format")
        try:
            patient_id = int(patient.split("/")[1])
        except (IndexError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid patient ID")

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
    return JSONResponse(content=remove_nulls(bundle.model_dump()), status_code=200, media_type="application/fhir+json") 