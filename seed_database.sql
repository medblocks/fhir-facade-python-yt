-- Create table with patients
CREATE TABLE patients (
  id SERIAL PRIMARY KEY,
  first_name VARCHAR(50) NOT NULL,
  last_name VARCHAR(50) NOT NULL,
  date_of_birth DATE
);
-- Create Blood Pressure table with foreign key to patients
CREATE TABLE blood_pressure (
  id SERIAL PRIMARY KEY,
  patient_id INTEGER REFERENCES patients(id),
  systolic INTEGER NOT NULL,
  diastolic INTEGER NOT NULL,
  date DATE NOT NULL
);
-- Create Heart Rate table with foreign key to patients
CREATE TABLE heart_rate (
  id SERIAL PRIMARY KEY,
  patient_id INTEGER REFERENCES patients(id),
  rate INTEGER NOT NULL,
  date DATE NOT NULL
);
-- Seed Patients Table with Data
INSERT INTO patients (first_name, last_name, date_of_birth)
VALUES ('John', 'Doe', '1980-01-01'),
  ('Jane', 'Doe', '1985-01-01'),
  ('Alice', 'Smith', '1990-01-01'),
  ('Bob', 'Smith', '1995-01-01');
-- Seed Blood Pressure Table with Data
INSERT INTO blood_pressure (patient_id, systolic, diastolic, date)
VALUES (1, 120, 80, '2020-01-01'),
  (2, 130, 85, '2020-01-01'),
  (3, 140, 90, '2020-01-01'),
  (4, 150, 95, '2020-01-01'),
  (1, 125, 85, '2020-01-02'),
  (2, 135, 90, '2020-01-02'),
  (3, 145, 95, '2020-01-02'),
  (4, 155, 100, '2020-01-02'),
  (1, 130, 90, '2020-01-03'),
  (2, 140, 95, '2020-01-03'),
  (3, 150, 100, '2020-01-03'),
  (4, 160, 105, '2020-01-03');
-- Seed Heart Rate Table with Data
INSERT INTO heart_rate (patient_id, rate, date)
VALUES (1, 60, '2020-01-01'),
  (2, 65, '2020-01-01'),
  (3, 70, '2020-01-01'),
  (4, 75, '2020-01-01'),
  (1, 65, '2020-01-02'),
  (2, 70, '2020-01-02'),
  (3, 75, '2020-01-02'),
  (4, 80, '2020-01-02'),
  (1, 70, '2020-01-03'),
  (2, 75, '2020-01-03'),
  (3, 80, '2020-01-03'),
  (4, 85, '2020-01-03');
-- retreive all blood pressure and heart rate values joined for patient 1