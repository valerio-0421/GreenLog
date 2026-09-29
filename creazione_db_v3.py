"""
Creazione del database GreenLog.

Rispetto alla versione originale, lo schema e' stato ESTESO per riflettere
tutti i campi utili presenti nel dataset (Dataset.zip) e per usare come
chiave primaria/esterna gli stessi codici alfanumerici presenti nei CSV
(es. "DRV00001", "TRK00012", ...) invece di un INT AUTO_INCREMENT.
Questo evita di dover ricostruire una mappatura tra i codici del dataset
e nuovi ID numerici quando si caricano i dati (vedi popola_database.py).

Le colonne che nel dataset contengono grandezze imperiali sono state
rinominate per riflettere l'unita' di misura europea che verra' salvata
da popola_database.py (es. weight_lbs -> peso_kg, tank_capacity_gallons ->
tank_capacity_litri, ecc.).

Gli ENUM sono stati mantenuti e adattati ai valori previsti dal dominio logistico.
"""
import os
from dotenv import load_dotenv
import mysql.connector

load_dotenv()  

conn = mysql.connector.connect(
    host=os.environ["DB_HOST"],
    user=os.environ["DB_USER"],
    root=os.environ["DB_ROOT"],
    password=os.environ["DB_PASSWORD"],
    database=os.environ["DB_NAME"]
)
cursor = conn.cursor()
print("Collegato al server MySQL")

cursor.execute("DROP DATABASE IF EXISTS GreenLog")
print("Database eliminato")

cursor.execute("CREATE DATABASE GreenLog")
print("Database creato")

cursor.execute("USE GreenLog")
print("Entro nel database")

query = [
    """
    CREATE TABLE drivers (
        driver_id VARCHAR(20) PRIMARY KEY,
        first_name VARCHAR(50) NOT NULL,
        last_name VARCHAR(50) NOT NULL,
        hire_date DATE,
        termination_date DATE,
        license_number VARCHAR(50) UNIQUE,
        license_state VARCHAR(2),
        date_of_birth DATE,
        home_terminal VARCHAR(100),
        employment_status ENUM('Active','On Leave','Suspended','Terminated'),
        cdl_class VARCHAR(10),
        years_experience INT
    );
    """,
    """
    CREATE TABLE customers (
        customer_id VARCHAR(20) PRIMARY KEY,
        customer_name VARCHAR(150) NOT NULL,
        customer_type ENUM('Dedicated','Contract','Spot'),
        credit_terms_days INT,
        primary_freight_type VARCHAR(100),
        account_status ENUM('Active','Inactive'),
        contract_start_date DATE,
        annual_revenue_potential_eur DECIMAL(12, 2)
    );
    """,
    """
    CREATE TABLE routes (
        route_id VARCHAR(20) PRIMARY KEY,
        origin_city VARCHAR(100) NOT NULL,
        origin_state VARCHAR(2) NOT NULL,
        destination_city VARCHAR(100) NOT NULL,
        destination_state VARCHAR(2) NOT NULL,
        typical_distance_km DECIMAL(10, 2),
        base_rate_per_km_eur DECIMAL(8, 4),
        fuel_surcharge_rate DECIMAL(6, 4),
        typical_transit_days INT
    );
    """,
    """
    CREATE TABLE trucks (
        truck_id VARCHAR(20) PRIMARY KEY,
        unit_number VARCHAR(20) NOT NULL UNIQUE,
        make VARCHAR(50) NOT NULL,
        model_year YEAR NOT NULL,
        vin VARCHAR(20) NOT NULL UNIQUE,
        acquisition_date DATE NOT NULL,
        acquisition_km DECIMAL(10,2) NOT NULL CHECK(acquisition_km >= 0),
        fuel_type VARCHAR(20) NOT NULL,
        tank_capacity_litri DECIMAL(8,2) CHECK(tank_capacity_litri > 0),
        status ENUM('Active','Maintenance','Inactive') DEFAULT 'Active',
        home_terminal VARCHAR(100)
    );
    """,
    """
    CREATE TABLE trailers (
        trailer_id VARCHAR(20) PRIMARY KEY,
        trailer_number VARCHAR(20) NOT NULL,
        trailer_type VARCHAR(30) NOT NULL,
        length_metri DECIMAL(5,2) CHECK(length_metri > 0),
        model_year YEAR,
        vin VARCHAR(20) UNIQUE,
        acquisition_date DATE,
        status ENUM('Active','Maintenance','Inactive') DEFAULT 'Active',
        current_location VARCHAR(100)
    );
    """,
    """
    CREATE TABLE facilities (
        facility_id VARCHAR(20) PRIMARY KEY,
        nome VARCHAR(150) NOT NULL,
        tipo VARCHAR(50),
        citta VARCHAR(100) NOT NULL,
        stato VARCHAR(2) NOT NULL,
        latitudine DECIMAL(9,6),
        longitudine DECIMAL(9,6),
        numero_banchine INT,
        orario_operativo VARCHAR(20)
    );
    """,
    """
    CREATE TABLE loads (
        load_id VARCHAR(20) PRIMARY KEY,
        customer_id VARCHAR(20) NOT NULL,
        route_id VARCHAR(20) NOT NULL,
        data_consegna DATE,
        tipo_carico VARCHAR(30),
        peso_kg DECIMAL(10, 2),
        pezzi INT,
        ricavo_eur DECIMAL(12, 2),
        supplemento_carburante_eur DECIMAL(10, 2),
        oneri_accessori_eur DECIMAL(10, 2),
        stato_carico VARCHAR(20),
        tipo_prenotazione VARCHAR(20),
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
        FOREIGN KEY (route_id) REFERENCES routes(route_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS trips (
        trip_id VARCHAR(20) PRIMARY KEY,
        load_id VARCHAR(20) NOT NULL,
        driver_id VARCHAR(20),
        truck_id VARCHAR(20),
        trailer_id VARCHAR(20),
        data_partenza DATE,
        distanza_km DECIMAL(8, 2),
        durata_min INT,
        consumo_litro DECIMAL(8, 3),
        consumo_l_100km DECIMAL(6, 2),
        velocita_media_kmh DECIMAL(6, 2),
        tempo_inattivita_min INT,
        stato_viaggio VARCHAR(20),
        FOREIGN KEY (load_id) REFERENCES loads(load_id),
        FOREIGN KEY (driver_id) REFERENCES drivers(driver_id),
        FOREIGN KEY (truck_id) REFERENCES trucks(truck_id),
        FOREIGN KEY (trailer_id) REFERENCES trailers(trailer_id)
    );
    """,
    """
    CREATE TABLE maintenance_records (
        maintenance_id VARCHAR(20) PRIMARY KEY,
        truck_id VARCHAR(20) NOT NULL,
        maintenance_date DATE NOT NULL,
        maintenance_type VARCHAR(30) NOT NULL,
        odometro_km DECIMAL(10,2) CHECK(odometro_km >= 0),
        labor_hours DECIMAL(5,2) CHECK(labor_hours >= 0),
        labor_cost_eur DECIMAL(10,2) CHECK(labor_cost_eur >= 0),
        parts_cost_eur DECIMAL(10,2) CHECK(parts_cost_eur >= 0),
        total_cost_eur DECIMAL(10,2) CHECK(total_cost_eur >= 0),
        facility_location VARCHAR(100),
        downtime_hours DECIMAL(6,2) CHECK(downtime_hours >= 0),
        service_description TEXT,
        CONSTRAINT fk_maintenance_truck
            FOREIGN KEY (truck_id) REFERENCES trucks(truck_id)
            ON DELETE CASCADE ON UPDATE CASCADE
    );
    """,
    """
    CREATE TABLE truck_utilization_metrics (
        truck_id VARCHAR(20) NOT NULL,
        month DATE NOT NULL,
        trips_completed INT DEFAULT 0 CHECK(trips_completed >= 0),
        total_km DECIMAL(10,2) CHECK(total_km >= 0),
        total_revenue_eur DECIMAL(12,2) CHECK(total_revenue_eur >= 0),
        average_l_100km DECIMAL(6,2) CHECK(average_l_100km >= 0),
        maintenance_events INT DEFAULT 0 CHECK(maintenance_events >= 0),
        maintenance_cost_eur DECIMAL(10,2) CHECK(maintenance_cost_eur >= 0),
        downtime_hours DECIMAL(6,2) CHECK(downtime_hours >= 0),
        utilization_rate_pct DECIMAL(5,2) CHECK(utilization_rate_pct >= 0),
        PRIMARY KEY (truck_id, month),
        CONSTRAINT fk_metrics_truck
            FOREIGN KEY (truck_id) REFERENCES trucks(truck_id)
            ON DELETE CASCADE ON UPDATE CASCADE
    );
    """,
    """
    CREATE TABLE fuel_purchases (
        fuel_purchase_id VARCHAR(20) PRIMARY KEY,
        trip_id VARCHAR(20) NOT NULL,
        truck_id VARCHAR(20),
        driver_id VARCHAR(20),
        purchase_date DATETIME,
        location_city VARCHAR(50),
        location_state VARCHAR(10),
        litri DECIMAL(12,3),
        prezzo_litro_eur DECIMAL(10,4),
        costo_totale_eur DECIMAL(15,2),
        fuel_card_number VARCHAR(30),

        CONSTRAINT fk_fuel_trip
            FOREIGN KEY (trip_id) REFERENCES trips(trip_id)
            ON UPDATE CASCADE ON DELETE RESTRICT,

        CONSTRAINT fk_fuel_truck
            FOREIGN KEY (truck_id) REFERENCES trucks(truck_id)
            ON UPDATE CASCADE ON DELETE RESTRICT,

        CONSTRAINT fk_fuel_driver
            FOREIGN KEY (driver_id) REFERENCES drivers(driver_id)
            ON UPDATE CASCADE ON DELETE RESTRICT
    );
    """,
    """
    CREATE TABLE delivery_events (
        event_id VARCHAR(20) PRIMARY KEY,
        load_id VARCHAR(20) NOT NULL,
        trip_id VARCHAR(20) NOT NULL,
        facility_id VARCHAR(20) NOT NULL,
        event_type VARCHAR(20),
        scheduled_time DATETIME(6),
        actual_time DATETIME(6),
        detention_minutes INT DEFAULT 0,
        on_time BOOLEAN,
        location_city VARCHAR(50),
        location_state VARCHAR(10),

        CONSTRAINT fk_event_load
            FOREIGN KEY (load_id) REFERENCES loads(load_id)
            ON UPDATE CASCADE ON DELETE RESTRICT,

        CONSTRAINT fk_event_trip
            FOREIGN KEY (trip_id) REFERENCES trips(trip_id)
            ON UPDATE CASCADE ON DELETE RESTRICT,

        CONSTRAINT fk_event_facility
            FOREIGN KEY (facility_id) REFERENCES facilities(facility_id)
            ON UPDATE CASCADE ON DELETE RESTRICT
    );
    """,
    """
    CREATE TABLE safety_incidents (
        incident_id VARCHAR(20) PRIMARY KEY,
        trip_id VARCHAR(20) NOT NULL,
        truck_id VARCHAR(20),
        driver_id VARCHAR(20),
        incident_date DATETIME,
        incident_type ENUM('Accident','DOT Violation','Equipment Damage','Moving Violation','Customer Complaint'),
        location_city VARCHAR(50),
        location_state VARCHAR(10),
        at_fault_flag BOOLEAN,
        injury_flag BOOLEAN,
        description TEXT,
        vehicle_damage_cost_eur DECIMAL(15,2),
        cargo_damage_cost_eur DECIMAL(15,2),
        claim_amount_eur DECIMAL(15,2),
        preventable_flag BOOLEAN,

        CONSTRAINT fk_incident_trip
            FOREIGN KEY (trip_id) REFERENCES trips(trip_id)
            ON UPDATE CASCADE ON DELETE RESTRICT,

        CONSTRAINT fk_incident_truck
            FOREIGN KEY (truck_id) REFERENCES trucks(truck_id)
            ON UPDATE CASCADE ON DELETE RESTRICT,

        CONSTRAINT fk_incident_driver
            FOREIGN KEY (driver_id) REFERENCES drivers(driver_id)
            ON UPDATE CASCADE ON DELETE RESTRICT
    );
    """,
    """
    CREATE TABLE driver_monthly_metrics (
        driver_id VARCHAR(20),
        mese DATE,
        tot_km DECIMAL(10,2),
        tot_trips INT,
        consumo_medio_l_100km DECIMAL(6,2),
        tot_carburante_litri DECIMAL(10,2),
        total_revenue_eur DECIMAL(12,2),
        percentuale_puntualita DECIMAL(5,2),
        tempo_inattivita_medio_h DECIMAL(6,2),
        PRIMARY KEY (driver_id, mese),
        FOREIGN KEY (driver_id) REFERENCES drivers(driver_id)
    );
    """,
    """
    CREATE TABLE digital_twin (
        truck_id VARCHAR(20) PRIMARY KEY,
        tot_km DECIMAL(10,2),
        consumo_medio_l_100km DECIMAL(8,2),
        tot_CO2_kg DECIMAL(10,2),
        punteggio_eco DECIMAL(5,2),
        percentuale_utilizzo DECIMAL(5,2),
        indice_manutenzione DECIMAL(5,2),
        ultimo_aggiornamento DATETIME,
        FOREIGN KEY (truck_id) REFERENCES trucks(truck_id)
    );
    """
]

for q in query:
    cursor.execute(q)
    print("Tabella creata")

print("Database completo!")
conn.commit()
conn.close()
