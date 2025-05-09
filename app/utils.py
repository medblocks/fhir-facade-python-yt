from datetime import date, datetime
from fastapi.responses import JSONResponse
import json
from fhir.resources.operationoutcome import OperationOutcome

class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that can handle date and datetime objects."""
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)

class FHIRJSONResponse(JSONResponse):
    """Custom JSONResponse that uses the CustomJSONEncoder to handle date serialization."""
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            cls=CustomJSONEncoder,
        ).encode("utf-8")

def create_operation_outcome(status_code: int, detail: str, diagnostic: str = None) -> tuple[OperationOutcome, int]:
    """
    Create a FHIR OperationOutcome resource for error responses.
    
    Args:
        status_code: HTTP status code
        detail: Error message for display
        diagnostic: Additional diagnostic information (optional)
        
    Returns:
        Tuple of (OperationOutcome resource, HTTP status code)
    """
    # Map HTTP status codes to FHIR issue severity and code
    if status_code >= 500:
        severity = "fatal"
        code = "exception"
    elif status_code >= 400:
        severity = "error"
        if status_code == 404:
            code = "not-found"
        elif status_code == 400:
            code = "invalid"
        elif status_code == 403:
            code = "forbidden"
        elif status_code == 401:
            code = "security"
        else:
            code = "processing"
    else:
        severity = "warning"
        code = "informational"
    
    # Create the outcome
    outcome = OperationOutcome.model_construct(
        issue=[{
            "severity": severity,
            "code": code,
            "diagnostics": diagnostic or detail,
            "details": {
                "text": detail
            }
        }]
    )
    
    return outcome, status_code

def fhir_error_handler(status_code: int, detail: str, diagnostic: str = None) -> FHIRJSONResponse:
    """
    Create a FHIR-compliant error response.
    
    Args:
        status_code: HTTP status code
        detail: Error message
        diagnostic: Additional diagnostic information (optional)
        
    Returns:
        FHIRJSONResponse with OperationOutcome
    """
    outcome, status_code = create_operation_outcome(status_code, detail, diagnostic)
    return FHIRJSONResponse(
        content=outcome.model_dump(exclude_none=True),
        status_code=status_code,
        media_type="application/fhir+json"
    ) 