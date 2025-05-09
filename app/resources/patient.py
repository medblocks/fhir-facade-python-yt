# CRUD & search logic -> Patient FHIR 
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Request, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select, extract
from sqlalchemy.ext.asyncio import AsyncSession
from fhir.resources.patient import Patient
from fhir.resources.bundle import Bundle, BundleEntry
from datetime import date, timedelta
import re

from ..db import get_db
from ..models import PatientModel
from ..utils import FHIRJSONResponse, fhir_error_handler

router = APIRouter()

def validate_fhir_date(date_str: str) -> bool:
    """
    Validates if a date string follows FHIR date format:
    YYYY, YYYY-MM, or YYYY-MM-DD
    """
    pattern = r"^([0-9]([0-9]([0-9][1-9]|[1-9]0)|[1-9]00)|[1-9]000)(-(0[1-9]|1[0-2])(-(0[1-9]|[1-2][0-9]|3[0-1]))?)?$"
    return bool(re.match(pattern, date_str))

def is_valid_date(date_str: str) -> bool:
    """
    Checks if a date string represents a valid date.
    For partial dates (YYYY or YYYY-MM), returns True.
    For full dates (YYYY-MM-DD), validates the actual date.
    """
    if not validate_fhir_date(date_str):
        return False
    
    parts = date_str.split('-')
    if len(parts) == 1:  # YYYY
        return True
    elif len(parts) == 2:  # YYYY-MM
        try:
            year, month = map(int, parts)
            return 1 <= month <= 12
        except ValueError:
            return False
    else:  # YYYY-MM-DD
        try:
            year, month, day = map(int, parts)
            return 1 <= month <= 12 and 1 <= day <= 31
        except ValueError:
            return False

# converts PatientModel to FHIR Patient - for /Patient/{patient_id}
def row_to_patient(db_patient: PatientModel) -> Patient:
    p = Patient.model_construct()
    p.id = str(db_patient.id)
    p.name = [{
        "family": db_patient.last_name,
        "given": [db_patient.first_name],
        "text": f"{db_patient.first_name} {db_patient.last_name}"
    }]
    if db_patient.date_of_birth:
        p.birthDate = db_patient.date_of_birth.isoformat() if isinstance(db_patient.date_of_birth, date) else str(db_patient.date_of_birth)
    # Add other fields if needed, e.g., gender, address
    return p

# Converts a list of PatientModel to a FHIR Bundle - For /Patient search
def to_bundle(resources: List, type_: str="searchset") -> Bundle:
    """Creates a FHIR Bundle from a list of resources."""
    # Convert each resource to a dict and ensure dates are serialized
    serialized_resources = [r.model_dump(exclude_none=True) for r in resources]
    return Bundle.model_construct(
        type=type_,
        total=len(resources),
        entry=[BundleEntry.model_construct(resource=r) for r in serialized_resources]
    )

# --- CRUD & Search Endpoints ---
#  --- Read Patient by ID ---
@router.get("/Patient/{patient_id}", response_model=Patient, summary="Read Patient", tags=["Patient"])
async def read_patient(patient_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PatientModel).where(PatientModel.id == patient_id))
    db_patient = result.scalar_one_or_none()
    if not db_patient:
        return fhir_error_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found"
        )
    patient = row_to_patient(db_patient)
    return FHIRJSONResponse(content=patient.model_dump(exclude_none=True), status_code=status.HTTP_200_OK)

#  --- Search Patients ---
@router.get("/Patient", response_model=Bundle, summary="Search Patients", tags=["Patient"])
async def search_patients(
    request: Request,
    family: Optional[str] = Query(None, description="Search by family name (case-insensitive, partial match)"),
    given: Optional[str] = Query(None, description="Search by given name (case-insensitive, partial match)"),
    birthdate: Optional[str] = Query(None, description="Search by birth date (YYYY, YYYY-MM, or YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db)
):
    query = select(PatientModel)

    if family:
        query = query.where(PatientModel.last_name.ilike(f"%{family}%"))
    if given:
        query = query.where(PatientModel.first_name.ilike(f"%{given}%"))
    if birthdate:
        if not validate_fhir_date(birthdate):
            return fhir_error_handler(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid birthdate format",
                diagnostic=f"Birthdate must be in YYYY, YYYY-MM, or YYYY-MM-DD format. Received: {birthdate}"
            )
        
        parts = birthdate.split('-')
        if len(parts) == 1:  # YYYY
            year = int(parts[0])
            # Create date range for the entire year
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)
            query = query.where(
                PatientModel.date_of_birth >= start_date,
                PatientModel.date_of_birth <= end_date
            )
        elif len(parts) == 2:  # YYYY-MM
            year, month = map(int, parts)
            # Create date range for the specific month
            start_date = date(year, month, 1)
            # Get the last day of the month
            if month == 12:
                end_date = date(year, month, 31)
            else:
                end_date = date(year, month + 1, 1) - timedelta(days=1)
            query = query.where(
                PatientModel.date_of_birth >= start_date,
                PatientModel.date_of_birth <= end_date
            )
        else:  # YYYY-MM-DD
            try:
                birth_date = date.fromisoformat(birthdate)
                query = query.where(PatientModel.date_of_birth == birth_date)
            except ValueError:
                return fhir_error_handler(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid birthdate",
                    diagnostic=f"Invalid calendar date: {birthdate}"
                )

    result = await db.execute(query)
    db_patients = result.scalars().all()
    patients = [row_to_patient(p) for p in db_patients]
    bundle = to_bundle(patients)
    return FHIRJSONResponse(content=bundle.model_dump(exclude_none=True), status_code=status.HTTP_200_OK)

@router.post("/Patient", status_code=status.HTTP_201_CREATED, response_model=Patient, summary="Create Patient", tags=["Patient"])
async def create_patient(resource: Patient, db: AsyncSession = Depends(get_db)):
    """
    Create a new Patient resource.
    """
    # Basic validation
    if not resource.name or not resource.name[0].family or not resource.name[0].given:
        return fhir_error_handler(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Patient resource",
            diagnostic="Patient resource must include at least one name with family and given name"
        )

    db_birth_date_for_model: Optional[date] = None
    if resource.birthDate:
        birth_date_input = resource.birthDate  # This is what's coming from the Patient model

        birth_date_str: str
        if isinstance(birth_date_input, date):  # Check if it's already a datetime.date object
            birth_date_str = birth_date_input.isoformat()
        elif hasattr(birth_date_input, 'as_json'):  # Check if it's a FHIR type with as_json()
            birth_date_str = birth_date_input.as_json()
        elif isinstance(birth_date_input, str): # Check if it's already a string
            birth_date_str = birth_date_input
        else:
            # This case should ideally not be reached if FHIR model parsing is consistent
            return fhir_error_handler(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal Server Error",
                diagnostic=f"Unexpected type for birthDate: {type(birth_date_input)}. Expected FHIR DateType, datetime.date, or string."
            )

        # 1. Validate general FHIR date format (YYYY, YYYY-MM, YYYY-MM-DD)
        if not validate_fhir_date(birth_date_str):
            return fhir_error_handler(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid birthDate format",
                diagnostic=f"Invalid birthDate format: '{birth_date_str}'. Must be YYYY, YYYY-MM, or YYYY-MM-DD."
            )
        
        # 2. Enforce full date (YYYY-MM-DD) for database storage
        date_parts = birth_date_str.split('-')
        if len(date_parts) != 3:
            return fhir_error_handler(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Partial dates not supported",
                diagnostic=f"Database requires a full birth date (YYYY-MM-DD). Received '{birth_date_str}'. Partial dates are not supported for creation."
            )
        
        # 3. Validate if the YYYY-MM-DD string is a valid calendar date and convert
        try:
            db_birth_date_for_model = date.fromisoformat(birth_date_str)
        except ValueError:
            # This catches invalid dates like "2023-02-30"
            return fhir_error_handler(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid birth date",
                diagnostic=f"Invalid birth date: '{birth_date_str}' is not a valid calendar date."
            )

    db_patient = PatientModel(
        first_name=resource.name[0].given[0],
        last_name=resource.name[0].family,
        date_of_birth=db_birth_date_for_model # Use the validated and converted date
    )
    db.add(db_patient)
    try:
        await db.commit()
        await db.refresh(db_patient)
    except Exception as e:
        await db.rollback()
        return fhir_error_handler(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database transaction failed",
            diagnostic=str(e)
        )

    created_patient = row_to_patient(db_patient)
    headers = {"Location": f"/Patient/{created_patient.id}"}
    return FHIRJSONResponse(content=created_patient.model_dump(exclude_none=True), status_code=status.HTTP_201_CREATED, headers=headers, media_type="application/fhir+json") 