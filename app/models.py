# SQLAlchemy ORM tables 
from sqlalchemy import Column, Integer, String, Date, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from .db import Base

class PatientModel(Base):
    __tablename__ = 'patients'

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    date_of_birth = Column(Date, nullable=False)

    blood_pressures = relationship("BloodPressureModel", back_populates="patient")
    heart_rates = relationship("HeartRateModel", back_populates="patient")

class BloodPressureModel(Base):
    __tablename__ = 'blood_pressure'

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey('patients.id'), nullable=False)
    systolic = Column(Float, nullable=False)
    diastolic = Column(Float, nullable=False)
    date = Column(Date, nullable=False)

    patient = relationship("PatientModel", back_populates="blood_pressures")

class HeartRateModel(Base):
    __tablename__ = 'heart_rate'

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey('patients.id'), nullable=False)
    rate = Column(Float, nullable=False)
    date = Column(Date, nullable=False)

    patient = relationship("PatientModel", back_populates="heart_rates") 