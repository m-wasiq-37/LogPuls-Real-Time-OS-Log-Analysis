# LogPuls – Real-Time OS Log Analysis

LogPuls is a web application for real-time operating system log ingestion, analysis, and visualization.  
It is designed for DevOps, system administrators, and developers who need instant insights from their servers and containers.

Built with **FastAPI**, **MongoDB**, and a **Vanilla JS frontend**, LogPuls offers an elegant dark dashboard powered by live WebSocket streams and powerful filtering tools.

<img width="1180" height="1742" alt="localhost_3000_dashboard html" src="https://github.com/user-attachments/assets/5dc50975-44a7-4ace-a506-cc8b46f5e11d" />

---

## Live Stack Overview

| Layer | Technology |
|-------|-------------|
| Backend | FastAPI (Python 3.11) |
| Database | MongoDB |
| Frontend | HTML, CSS, Vanilla JS |
| Realtime | WebSocket |
| Auth | JWT + bcrypt |
| Containers | Docker + Docker Compose |
| Proxy | Nginx (single-link deployment) |

---

## Features

- **Single Unified URL** – Everything runs under `http://localhost:3000`  
- **Secure Login** – JWT-based authentication  
- **Dynamic Dashboard** – Live table and charts with real-time updates  
- **Filtering Tools** – Filter by level, keyword, date range, or source  
- **Auto-Refresh & Auto-Scroll** – Control live updates as needed  
- **Color-Coded Logs** – INFO (blue), WARNING (orange), ERROR (red)  
- **Historical Data** – Over 100,000 seeded logs across a full year  
- **Agent Support** – Ingest logs from Windows or Docker containers  

---

## Project Structure

```bash
LogPuls/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── auth.py
│   │   ├── db.py
│   │   ├── models.py
│   │   ├── logs.py
│   │   └── websocket.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── seed_user.py
│
├── frontend/
│   ├── index.html
│   ├── login.html
│   ├── dashboard.html
│   ├── js/
│   │   ├── login.js
│   │   ├── dashboard.js
│   │   └── api.js
│   ├── css/
│   │   ├── style.css
│   │   └── dashboard.css
│   ├── Dockerfile
│
├── agent/
│   ├── agent.py
│   └── sample_logs.py
│
├── docker-compose.yml
├── .env
└── README.md
````

---

## Environment Configuration

All runtime settings are stored in `.env`:

```bash
MONGO_URI=mongodb://mongodb:27017/logpuls
JWT_SECRET=logpulssecret
ADMIN_USER=MWasiq
ADMIN_PASS=1122
```

---

## Run with Docker

### 1. Build and Launch

```bash
docker compose up --build
```

### 2. Access the App

Once all containers start, open:

```
http://localhost:3000
```

### 3. Login Credentials

```bash
Username: MWasiq
Password: 1122
```

---

## Agent Setup (Optional)

For live system integration, deploy the agent on a Windows or Linux host.

* Windows Agent reads system event logs (via pywin32).
* Docker Agent uses `sample_logs.py` for testing environments.
* Logs are periodically pushed to the backend at `/api/logs/ingest`.

---

## Dashboard Overview

* **Filters:** keyword search, log level, date/time, source
* **Charts:** log level distribution, source activity, time-based trends
* **Real-Time Feed:** logs stream instantly over WebSockets
* **Responsive Layout:** optimized for desktops and laptops

---

## Developer Notes

* Backend and frontend are both containerized.
* Nginx handles static files and routes API/WebSocket traffic to FastAPI.
* MongoDB stores both users and logs.
* The seeding script automatically creates an admin user and log data.

---

## Tech Highlights

* Asynchronous backend using FastAPI + Motor
* Secure JWT authentication with bcrypt password hashing
* Live WebSockets for instant log updates
* MongoDB aggregations for analytics and filtering
* Zero-framework frontend – pure HTML, CSS, and JavaScript

---

## Example Commands

**Rebuild all containers:**

```bash
docker compose up --build --force-recreate
```

**Clean up all resources:**

```bash
docker compose down -v
```

---

## License

MIT License © 2025 Muhammad Wasiq

---

## Author

**Muhammad Wasiq**, **Muhammad Huzaifa**.
Bahria University, Lahore Campus.
BSCS – 7th Semester.
