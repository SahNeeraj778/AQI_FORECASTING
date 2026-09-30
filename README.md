# Delhi NCR 72-Hour AQI Forecasting System

> An intelligent air-quality forecasting system for Delhi NCR that combines air-pollution and meteorological data to predict future PM2.5 and AQI conditions.

[![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-FF4B4B?logo=streamlit)](https://streamlit.io/)
[![XGBoost](https://img.shields.io/badge/ML-XGBoost-orange)](https://xgboost.readthedocs.io/)
[![Deployed](https://img.shields.io/badge/Status-Live-brightgreen)](#deployment)

**Smart India Hackathon 2026 · Problem ID: SIH26082 — Delhi NCR Heat & Air Early Warning System**

---

## Table of Contents

- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [Current MVP](#current-mvp)
- [System Architecture](#system-architecture)
- [Data Sources](#data-sources)
- [Machine Learning](#machine-learning)
- [AQI Forecasting](#aqi-forecasting)
- [Dashboard](#dashboard)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Running the Dashboard](#running-the-dashboard)
- [Deployment](#deployment)
- [API](#api)
- [Development Roadmap](#development-roadmap)
- [Future Vision](#future-vision)
- [Limitations](#limitations)
- [Project Status](#project-status)
- [Acknowledgements](#acknowledgements)
- [Links](#links)

---

## Overview

Delhi NCR frequently experiences severe air-pollution episodes, particularly during the winter season. Traditional air-quality forecasting approaches often model pollution and meteorological conditions independently, even though the two are strongly interconnected.

Atmospheric conditions such as temperature, wind speed, and boundary-layer behavior influence how pollutants disperse or accumulate. At the same time, high concentrations of aerosols can influence local atmospheric conditions.

This project develops an integrated forecasting system that provides a **72-hour outlook** for Delhi NCR, combining pollution observations with meteorological information and machine-learning techniques.

The current implementation focuses on building a reliable PM2.5 and AQI forecasting MVP, with a roadmap toward more advanced meteorology-chemistry coupling.

## Problem Statement

During severe pollution events in Delhi NCR:

- Atmospheric inversion can trap pollutants close to the surface.
- Low wind speeds reduce pollutant dispersion.
- A shallow planetary boundary layer (PBL) can increase near-surface pollutant concentrations.
- Regional sources such as crop-residue (stubble) burning can contribute to pollution episodes.
- Meteorological conditions significantly affect the transport and accumulation of particulate matter.

A forecasting system that considers both pollution and weather conditions provides more useful predictions than relying on historical pollutant concentrations alone.

The long-term goal is a **coupled forecasting framework** capable of representing interactions between:

| Meteorology | Air Quality |
|---|---|
| Temperature | PM2.5 |
| Wind | PM10 |
| Planetary Boundary Layer (PBL) characteristics | O₃ |
| Atmospheric stability / inversion | NOx |

## Current MVP

The current version focuses on a practical machine-learning pipeline rather than immediately implementing a computationally intensive atmospheric chemistry model.

**Capabilities:**

- Historical PM2.5 data processing
- Weather-data integration
- Feature engineering
- XGBoost-based forecasting
- PM2.5 prediction and AQI calculation
- 72-hour forecasting workflow
- FastAPI backend + Streamlit dashboard
- Delhi NCR–focused data from OpenAQ, Open-Meteo, and CPCB

The forecast horizon and prediction configuration are still being refined and will be updated as the model and dashboard evolve.

## System Architecture

```
                    ┌─────────────────────┐
                    │    Data Sources      │
                    │  OpenAQ · CPCB       │
                    │  Open-Meteo          │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Data Processing &   │
                    │ Feature Engineering  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     ML Model         │
                    │  XGBoost · PM2.5     │
                    │    Forecasting       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  AQI Calculation     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  FastAPI Backend     │
                    │ Data · Forecast ·    │
                    │ Health · Alerts      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Streamlit Dashboard  │
                    │ AQI · PM2.5 ·        │
                    │ Forecast · Weather   │
                    └─────────────────────┘
```

## Data Sources

| Source | Purpose |
|---|---|
| **OpenAQ** | Air-quality observations |
| **CPCB** | Indian air-quality reference data |
| **Open-Meteo** | Historical and forecast meteorological data |

The current MVP primarily focuses on PM2.5 while incorporating weather features into the forecasting pipeline.

## Machine Learning

**Model:** [XGBoost](https://xgboost.readthedocs.io/), a gradient-boosted decision-tree algorithm well suited to structured/tabular data.

**Current prediction targets:**
- PM2.5 forecasts
- AQI forecasts derived from predicted pollution levels

**Features:**
- Historical and lagged PM2.5 values
- Rolling PM2.5 statistics
- Temperature and wind-related variables
- Time-of-day and day-of-week features
- Other available meteorological variables

**Model evaluation:** Formal metrics are not yet finalized. Planned metrics include MAE, RMSE, R², and forecast error across time horizons — to be added once a full evaluation procedure is complete.

## AQI Forecasting

The system converts predicted pollutant concentrations into AQI to make model output easier to interpret. The dashboard surfaces:

- Current air-quality conditions
- Predicted PM2.5 and AQI
- Future air-quality trends
- Meteorological conditions

The AQI implementation will continue to be refined as additional pollutant data becomes available.

## Dashboard

The project includes a **Streamlit** dashboard that makes model predictions accessible without requiring users to interact directly with the ML pipeline. It currently includes:

- 🌍 Geospatial risk map of monitored zones across Delhi NCR
- 📈 Forecast and analytics views
- 🔥 Thermal stress panel
- 🚨 Advisories
- Station-level ranking table (temperature, AQI, PM2.5, thermal stress)

**Live demo:**
👉 [sih26082-disasterforecast.streamlit.app](https://sih26082-disasterforecast-lrmoutdcqhzthdvit3gwzs.streamlit.app/)

The dashboard is connected to the live FastAPI backend hosted on Render — see [Deployment](#deployment).

> Note: Some values shown in early builds of the dashboard are synthetic/demonstration data used for UI prototyping and are not yet operational public-safety forecasts.

## Project Structure

```
SIH26082-DisasterForecast/
│
├── backened/
│   ├── config.py
│   ├── main.py
│   ├── requirements.txt
│   │
│   └── app/
│       ├── __init__.py
│       │
│       ├── routes/
│       │   ├── alerts.py
│       │   ├── data.py
│       │   ├── forecast.py
│       │   ├── health.py
│       │   └── __init__.py
│       │
│       ├── schemas/
│       │   └── models.py
│       │
│       ├── services/
│       │   ├── alert_service.py
│       │   ├── data_service.py
│       │   ├── model_service.py
│       │   ├── wbgt_service.py
│       │   └── __init__.py
│       │
│       └── utils/
│           └── wbgt.py
│
├── frontened/
│   └── src/
│       └── main.py
│
├── ml/
│   ├── data/
│   │   ├── delhi_master_dataset.csv
│   │   ├── delhi_master_dataset_v3.csv.xls
│   │   └── delhi_pm25_features.csv
│   │
│   ├── model/
│   │   ├── metadata.json
│   │   └── xgb_model.joblib
│   │
│   └── notebooks/
│       └── model_v4_improved.ipynb
│
├── .gitignore
├── requirements.txt
└── README.md
```

## Tech Stack

| Category | Tools |
|---|---|
| **Language** | Python |
| **ML / Data Processing** | Pandas, NumPy, Scikit-learn, XGBoost, Joblib |
| **Backend** | FastAPI, Uvicorn, Pydantic |
| **Frontend** | Streamlit |
| **Visualization** | Plotly, PyDeck |
| **Data Sources** | OpenAQ, Open-Meteo, CPCB |
| **Development** | Git, GitHub, VS Code |

## Installation

**1. Clone the repository**

```bash
git clone https://github.com/sourav27900/SIH26082-DisasterForecast.git
cd SIH26082-DisasterForecast
```

**2. Create a virtual environment** (Windows)

```bash
python -m venv .venv
.venv\Scripts\activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

### Configuration

API credentials and environment-specific settings should never be committed to the repository. Copy `.env.example` to `.env` (create one if it doesn't exist yet) and set the values relevant to your setup:

| Variable | Purpose |
|---|---|
| `OPENAQ_API_KEY` | Auth key for pulling air-quality observations from OpenAQ |
| `BACKEND_URL` | FastAPI base URL the Streamlit dashboard calls (defaults to `http://127.0.0.1:8000` locally; set to the Render URL in production) |
| `FORECAST_HORIZON_HOURS` | Number of hours ahead the model forecasts (currently 72) |

Do not place real API keys directly inside Python source files. As the pipeline grows (e.g. weather-data refresh cadence, alert thresholds), add new knobs here rather than hardcoding them.

## Running the Dashboard

From the frontend directory:

```bash
streamlit run src/main.py
```

The Streamlit application will normally be available at:

```
http://localhost:8501
```

> The exact startup commands may evolve as the project architecture is finalized.

## Deployment

The system is live, with the frontend and backend deployed separately and connected to each other.

| Component | Platform | URL |
|---|---|---|
| **Frontend** (Streamlit dashboard) | Streamlit Community Cloud | [sih26082-disasterforecast.streamlit.app](https://sih26082-disasterforecast-lrmoutdcqhzthdvit3gwzs.streamlit.app/) |
| **Backend** (FastAPI) | Render | [disasterforecast-api.onrender.com](https://disasterforecast-api.onrender.com) |

The backend exposes interactive API docs at `/docs` — available live at [disasterforecast-api.onrender.com/docs](https://disasterforecast-api.onrender.com/docs).

> Render's free tier spins down after inactivity, so the first request after idle time may take a few seconds longer while the service wakes up.

## API

The backend is organized around several route groups:

```
/routes
├── alerts
├── data
├── forecast
└── health
```

These form the foundation for connecting the machine-learning pipeline to the user-facing dashboard. FastAPI's auto-generated docs are available at `/docs` when the backend is running.

## Development Roadmap

**Phase 1 — Current MVP**
- [x] PM2.5 data pipeline
- [x] Data cleaning
- [x] Feature engineering
- [x] Weather-data integration
- [x] XGBoost forecasting
- [x] AQI calculation
- [x] FastAPI backend
- [x] Streamlit dashboard

**Phase 2 — Improved Forecasting**
- [ ] Formal model evaluation
- [ ] Optimize forecast horizon
- [ ] Improve multi-step forecasting
- [ ] Add additional pollutant variables
- [ ] Improve station-level forecasting
- [ ] Improve uncertainty/error analysis

**Phase 3 — Atmospheric Intelligence**
- [ ] Atmospheric inversion detection
- [ ] PBL-height integration
- [ ] Improved pollutant-dispersion indicators
- [ ] Wind-based pollution transport analysis
- [ ] Regional pollution-source analysis
- [ ] Stubble-burning influence analysis

**Phase 4 — Advanced Coupled Forecasting**

Long-term goal: investigate integration with open-source atmospheric modeling frameworks such as WRF-Chem, to enable advanced modeling of meteorology–chemistry interactions.

## Future Vision

The long-term objective is a high-resolution forecasting platform that goes beyond simply predicting AQI — one that can answer questions such as:

- How severe will pollution be over the next 72 hours?
- Will meteorological conditions allow pollutants to disperse or become trapped?
- How strong is the atmospheric inversion?
- How might regional pollution transport affect Delhi NCR?
- What are the likely pollution hotspots under the predicted weather conditions?

This would transform the platform from a conventional AQI prediction dashboard into a comprehensive air-quality intelligence and decision-support system.

## Limitations

This is an MVP and does not yet implement the full coupled atmospheric-chemistry system described in the original challenge:

- Limited historical training data
- Model performance evaluation still in progress
- PM2.5 is the primary forecasting focus
- Advanced atmospheric inversion modeling not yet implemented
- Full PBL dynamics not yet modeled
- Stubble-burning plume simulation not yet implemented
- Full WRF-Chem integration not currently implemented
- Forecast accuracy requires further validation

## Project Status

**Current status:** 🟢 Active Development

```
Data Pipeline → Weather Integration → XGBoost Model → AQI → FastAPI → Streamlit Dashboard
```

## Acknowledgements

This project is being developed for the **Smart India Hackathon (SIH)**, addressing air-quality forecasting challenges in Delhi NCR. Data and technical resources are drawn from publicly available platforms and open-source technologies, including OpenAQ, Open-Meteo, CPCB, XGBoost, FastAPI, and Streamlit.

## Links

- **GitHub Repository:** # Delhi NCR 72-Hour AQI Forecasting System

> An intelligent air-quality forecasting system for Delhi NCR that combines air-pollution and meteorological data to predict future PM2.5 and AQI conditions.

[![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-FF4B4B?logo=streamlit)](https://streamlit.io/)
[![XGBoost](https://img.shields.io/badge/ML-XGBoost-orange)](https://xgboost.readthedocs.io/)
[![Deployed](https://img.shields.io/badge/Status-Live-brightgreen)](#deployment)

**Smart India Hackathon 2026 · Problem ID: SIH26082 — Delhi NCR Heat & Air Early Warning System**

---

## Table of Contents

- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [Current MVP](#current-mvp)
- [System Architecture](#system-architecture)
- [Data Sources](#data-sources)
- [Machine Learning](#machine-learning)
- [AQI Forecasting](#aqi-forecasting)
- [Dashboard](#dashboard)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Running the Dashboard](#running-the-dashboard)
- [Deployment](#deployment)
- [API](#api)
- [Development Roadmap](#development-roadmap)
- [Future Vision](#future-vision)
- [Limitations](#limitations)
- [Project Status](#project-status)
- [Acknowledgements](#acknowledgements)
- [Links](#links)

---

## Overview

Delhi NCR frequently experiences severe air-pollution episodes, particularly during the winter season. Traditional air-quality forecasting approaches often model pollution and meteorological conditions independently, even though the two are strongly interconnected.

Atmospheric conditions such as temperature, wind speed, and boundary-layer behavior influence how pollutants disperse or accumulate. At the same time, high concentrations of aerosols can influence local atmospheric conditions.

This project develops an integrated forecasting system that provides a **72-hour outlook** for Delhi NCR, combining pollution observations with meteorological information and machine-learning techniques.

The current implementation focuses on building a reliable PM2.5 and AQI forecasting MVP, with a roadmap toward more advanced meteorology-chemistry coupling.

## Problem Statement

During severe pollution events in Delhi NCR:

- Atmospheric inversion can trap pollutants close to the surface.
- Low wind speeds reduce pollutant dispersion.
- A shallow planetary boundary layer (PBL) can increase near-surface pollutant concentrations.
- Regional sources such as crop-residue (stubble) burning can contribute to pollution episodes.
- Meteorological conditions significantly affect the transport and accumulation of particulate matter.

A forecasting system that considers both pollution and weather conditions provides more useful predictions than relying on historical pollutant concentrations alone.

The long-term goal is a **coupled forecasting framework** capable of representing interactions between:

| Meteorology | Air Quality |
|---|---|
| Temperature | PM2.5 |
| Wind | PM10 |
| Planetary Boundary Layer (PBL) characteristics | O₃ |
| Atmospheric stability / inversion | NOx |

## Current MVP

The current version focuses on a practical machine-learning pipeline rather than immediately implementing a computationally intensive atmospheric chemistry model.

**Capabilities:**

- Historical PM2.5 data processing
- Weather-data integration
- Feature engineering
- XGBoost-based forecasting
- PM2.5 prediction and AQI calculation
- 72-hour forecasting workflow
- FastAPI backend + Streamlit dashboard
- Delhi NCR–focused data from OpenAQ, Open-Meteo, and CPCB

The forecast horizon and prediction configuration are still being refined and will be updated as the model and dashboard evolve.

## System Architecture

```
                    ┌─────────────────────┐
                    │    Data Sources      │
                    │  OpenAQ · CPCB       │
                    │  Open-Meteo          │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Data Processing &   │
                    │ Feature Engineering  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     ML Model         │
                    │  XGBoost · PM2.5     │
                    │    Forecasting       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  AQI Calculation     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  FastAPI Backend     │
                    │ Data · Forecast ·    │
                    │ Health · Alerts      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Streamlit Dashboard  │
                    │ AQI · PM2.5 ·        │
                    │ Forecast · Weather   │
                    └─────────────────────┘
```

## Data Sources

| Source | Purpose |
|---|---|
| **OpenAQ** | Air-quality observations |
| **CPCB** | Indian air-quality reference data |
| **Open-Meteo** | Historical and forecast meteorological data |

The current MVP primarily focuses on PM2.5 while incorporating weather features into the forecasting pipeline.

## Machine Learning

**Model:** [XGBoost](https://xgboost.readthedocs.io/), a gradient-boosted decision-tree algorithm well suited to structured/tabular data.

**Current prediction targets:**
- PM2.5 forecasts
- AQI forecasts derived from predicted pollution levels

**Features:**
- Historical and lagged PM2.5 values
- Rolling PM2.5 statistics
- Temperature and wind-related variables
- Time-of-day and day-of-week features
- Other available meteorological variables

**Model evaluation:** Formal metrics are not yet finalized. Planned metrics include MAE, RMSE, R², and forecast error across time horizons — to be added once a full evaluation procedure is complete.

## AQI Forecasting

The system converts predicted pollutant concentrations into AQI to make model output easier to interpret. The dashboard surfaces:

- Current air-quality conditions
- Predicted PM2.5 and AQI
- Future air-quality trends
- Meteorological conditions

The AQI implementation will continue to be refined as additional pollutant data becomes available.

## Dashboard

The project includes a **Streamlit** dashboard that makes model predictions accessible without requiring users to interact directly with the ML pipeline. It currently includes:

- 🌍 Geospatial risk map of monitored zones across Delhi NCR
- 📈 Forecast and analytics views
- 🔥 Thermal stress panel
- 🚨 Advisories
- Station-level ranking table (temperature, AQI, PM2.5, thermal stress)

**Live demo:**
👉 [sih26082-disasterforecast.streamlit.app](https://sih26082-disasterforecast-lrmoutdcqhzthdvit3gwzs.streamlit.app/)

The dashboard is connected to the live FastAPI backend hosted on Render — see [Deployment](#deployment).

> Note: Some values shown in early builds of the dashboard are synthetic/demonstration data used for UI prototyping and are not yet operational public-safety forecasts.

## Project Structure

```
SIH26082-DisasterForecast/
│
├── backened/
│   ├── config.py
│   ├── main.py
│   ├── requirements.txt
│   │
│   └── app/
│       ├── __init__.py
│       │
│       ├── routes/
│       │   ├── alerts.py
│       │   ├── data.py
│       │   ├── forecast.py
│       │   ├── health.py
│       │   └── __init__.py
│       │
│       ├── schemas/
│       │   └── models.py
│       │
│       ├── services/
│       │   ├── alert_service.py
│       │   ├── data_service.py
│       │   ├── model_service.py
│       │   ├── wbgt_service.py
│       │   └── __init__.py
│       │
│       └── utils/
│           └── wbgt.py
│
├── frontened/
│   └── src/
│       └── main.py
│
├── ml/
│   ├── data/
│   │   ├── delhi_master_dataset.csv
│   │   ├── delhi_master_dataset_v3.csv.xls
│   │   └── delhi_pm25_features.csv
│   │
│   ├── model/
│   │   ├── metadata.json
│   │   └── xgb_model.joblib
│   │
│   └── notebooks/
│       └── model_v4_improved.ipynb
│
├── .gitignore
├── requirements.txt
└── README.md
```

## Tech Stack

| Category | Tools |
|---|---|
| **Language** | Python |
| **ML / Data Processing** | Pandas, NumPy, Scikit-learn, XGBoost, Joblib |
| **Backend** | FastAPI, Uvicorn, Pydantic |
| **Frontend** | Streamlit |
| **Visualization** | Plotly, PyDeck |
| **Data Sources** | OpenAQ, Open-Meteo, CPCB |
| **Development** | Git, GitHub, VS Code |

## Installation

**1. Clone the repository**

```bash
git clone https://github.com/sourav27900/SIH26082-DisasterForecast.git
cd SIH26082-DisasterForecast
```

**2. Create a virtual environment** (Windows)

```bash
python -m venv .venv
.venv\Scripts\activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

### Configuration

API credentials and environment-specific settings should never be committed to the repository. Copy `.env.example` to `.env` (create one if it doesn't exist yet) and set the values relevant to your setup:

| Variable | Purpose |
|---|---|
| `OPENAQ_API_KEY` | Auth key for pulling air-quality observations from OpenAQ |
| `BACKEND_URL` | FastAPI base URL the Streamlit dashboard calls (defaults to `http://127.0.0.1:8000` locally; set to the Render URL in production) |
| `FORECAST_HORIZON_HOURS` | Number of hours ahead the model forecasts (currently 72) |

Do not place real API keys directly inside Python source files. As the pipeline grows (e.g. weather-data refresh cadence, alert thresholds), add new knobs here rather than hardcoding them.

## Running the Dashboard

From the frontend directory:

```bash
streamlit run src/main.py
```

The Streamlit application will normally be available at:

```
http://localhost:8501
```

> The exact startup commands may evolve as the project architecture is finalized.

## Deployment

The system is live, with the frontend and backend deployed separately and connected to each other.

| Component | Platform | URL |
|---|---|---|
| **Frontend** (Streamlit dashboard) | Streamlit Community Cloud | [sih26082-disasterforecast.streamlit.app](https://sih26082-disasterforecast-lrmoutdcqhzthdvit3gwzs.streamlit.app/) |
| **Backend** (FastAPI) | Render | [disasterforecast-api.onrender.com](https://disasterforecast-api.onrender.com) |

The backend exposes interactive API docs at `/docs` — available live at [disasterforecast-api.onrender.com/docs](https://disasterforecast-api.onrender.com/docs).

> Render's free tier spins down after inactivity, so the first request after idle time may take a few seconds longer while the service wakes up.

## API

The backend is organized around several route groups:

```
/routes
├── alerts
├── data
├── forecast
└── health
```

These form the foundation for connecting the machine-learning pipeline to the user-facing dashboard. FastAPI's auto-generated docs are available at `/docs` when the backend is running.

## Development Roadmap

**Phase 1 — Current MVP**
- [x] PM2.5 data pipeline
- [x] Data cleaning
- [x] Feature engineering
- [x] Weather-data integration
- [x] XGBoost forecasting
- [x] AQI calculation
- [x] FastAPI backend
- [x] Streamlit dashboard

**Phase 2 — Improved Forecasting**
- [ ] Formal model evaluation
- [ ] Optimize forecast horizon
- [ ] Improve multi-step forecasting
- [ ] Add additional pollutant variables
- [ ] Improve station-level forecasting
- [ ] Improve uncertainty/error analysis

**Phase 3 — Atmospheric Intelligence**
- [ ] Atmospheric inversion detection
- [ ] PBL-height integration
- [ ] Improved pollutant-dispersion indicators
- [ ] Wind-based pollution transport analysis
- [ ] Regional pollution-source analysis
- [ ] Stubble-burning influence analysis

**Phase 4 — Advanced Coupled Forecasting**

Long-term goal: investigate integration with open-source atmospheric modeling frameworks such as WRF-Chem, to enable advanced modeling of meteorology–chemistry interactions.

## Future Vision

The long-term objective is a high-resolution forecasting platform that goes beyond simply predicting AQI — one that can answer questions such as:

- How severe will pollution be over the next 72 hours?
- Will meteorological conditions allow pollutants to disperse or become trapped?
- How strong is the atmospheric inversion?
- How might regional pollution transport affect Delhi NCR?
- What are the likely pollution hotspots under the predicted weather conditions?

This would transform the platform from a conventional AQI prediction dashboard into a comprehensive air-quality intelligence and decision-support system.

## Limitations

This is an MVP and does not yet implement the full coupled atmospheric-chemistry system described in the original challenge:

- Limited historical training data
- Model performance evaluation still in progress
- PM2.5 is the primary forecasting focus
- Advanced atmospheric inversion modeling not yet implemented
- Full PBL dynamics not yet modeled
- Stubble-burning plume simulation not yet implemented
- Full WRF-Chem integration not currently implemented
- Forecast accuracy requires further validation

## Project Status

**Current status:** 🟢 Active Development

```
Data Pipeline → Weather Integration → XGBoost Model → AQI → FastAPI → Streamlit Dashboard
```

## Acknowledgements

This project is being developed for the **Smart India Hackathon (SIH)**, addressing air-quality forecasting challenges in Delhi NCR. Data and technical resources are drawn from publicly available platforms and open-source technologies, including OpenAQ, Open-Meteo, CPCB, XGBoost, FastAPI, and Streamlit.

## Links

## Links

* **GitHub Repository:**
  https://github.com/SahNeeraj778/AQI_FORECASTING.git

* **Live Application:**
  https://aqi-forecasting-r5rt.onrender.com/
