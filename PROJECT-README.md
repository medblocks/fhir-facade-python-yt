# FHIR Facade Project

This project implements a FHIR facade over a PostgreSQL database using FastAPI in Python.

## Implemented Features

1. **Patient Resource**
   - `/Patient` endpoint with search parameters: `given`, `family`, and `birthdate`
   - `/Patient/{id}` endpoint to get a specific patient
   - `/Patient` POST endpoint to create a new patient

2. **Observation Resource**
   - `/Observation` endpoint with search parameters: `patient`, `code`, and `date`
   - `/Observation/{id}` endpoint to get a specific observation
