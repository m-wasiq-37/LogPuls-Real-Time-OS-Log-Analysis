# LogPuls - Real-Time OS Log Analysis

A real-time Windows log analyzer that collects Windows Event Viewer logs, stores them in MongoDB, and displays them on a responsive web dashboard with charts, tables, and ML-based anomaly detection.

## Features

- Real-time Log Collection: Automatically collects Windows Event Viewer logs (System, Application, Security)
- MongoDB Storage: All logs are saved to MongoDB for persistence and analysis
- Responsive Dashboard: Modern, responsive web interface with charts and tables
- Advanced Filtering: Filter logs by type, date, level, event ID, provider, and message (filters apply to charts and tables)
- ML Anomaly Detection: Simple ML model analyzes logs and displays warnings
- Authentication: Simple password-based login (password stored in `.env`)
- Dockerized: Everything runs in Docker containers
- Duplicate Prevention: Automatic duplicate detection and prevention

## Quick Start

**1. Create `.env` file:**
```bash
LOGIN_PASSWORD=wasiq123
```

**2. Start Windows Log Collector (required - run in separate terminal):**

**Option 1 - Using CMD/Batch file (recommended - double-click or run from CMD):**
```bash
start-windows-collector.cmd
```

**Option 2 - Using PowerShell:**
```bash
powershell -ExecutionPolicy Bypass -File .\start-windows-collector.ps1
```

**Option 3 - Manual:**
```bash
python agent\windows_collector_server.py
```

**3. Start Docker services:**
```bash
docker-compose up --build
```

**4. Access the application:**
- **Frontend**: http://localhost:1234
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Login Password**: `admin123` (from `.env`)

**5. Collect logs:**
Click the "Refresh Logs" button in the dashboard to collect Windows Event Viewer logs.

**To run in background:**
```bash
docker-compose up --build -d
```

**To stop:**
```bash
docker-compose down
```

## Project Structure

```
.
├── backend/              # FastAPI backend
│   └── app/
│       ├── main.py      # Main FastAPI application
│       ├── db.py        # MongoDB database operations
│       ├── auth.py      # Authentication
│       ├── logs.py      # ML analysis
│       └── websocket.py # WebSocket for real-time updates
├── agent/               # Log collection agent
│   ├── agent.py        # Agent to call Windows log collector server
│   └── windows_collector_server.py # HTTP server for Windows log collection
├── frontend/            # Frontend files
│   ├── index.html      # Login page
│   ├── dashboard.html  # Main dashboard
│   └── css/
│       └── style.css   # Styles
├── docker-compose.yml   # Docker Compose configuration
├── Dockerfile          # Docker image definition
├── requirements.txt    # Python dependencies
├── startup.py         # MongoDB wait script
├── start-windows-collector.ps1 # PowerShell script to start Windows collector
└── README.md           # This file
```

## Architecture

1. **Windows Log Collector Server**: HTTP server (runs on Windows host) that collects Event Viewer logs using win32evtlog
2. **Backend API**: FastAPI application (runs in Docker) that:
   - Calls Windows log collector server via HTTP when collecting logs
   - Stores logs in MongoDB with duplicate prevention
   - Provides REST API for frontend
   - Performs ML analysis on logs
3. **Frontend**: Responsive HTML/CSS/JavaScript dashboard with:
   - Login page
   - Dashboard with charts (Pie, Bar, Line) that update with filters
   - Log table with filtering
   - Real-time updates via WebSocket
4. **MongoDB**: Database for storing all collected logs

## Services

- **mongodb**: MongoDB database (port 27017)
- **backend**: FastAPI backend (port 8000)
- **frontend**: Nginx web server (port 1234)
- **Windows Collector**: HTTP server on Windows host (port 5001)

## API Endpoints

- `POST /api/login` - Login with password
- `POST /api/logs/collect` - Collect logs from Windows
- `GET /api/logs` - Get logs with optional filters
- `GET /api/stats` - Get log statistics (supports filters)
- `GET /api/analysis` - Get ML analysis results
- `GET /api/health` - Health check
- `WS /ws` - WebSocket for real-time updates

## Prerequisites

- Docker Desktop for Windows
- Windows OS (for log collection)
- Python 3.9+ with pywin32 installed on Windows host
- PowerShell (comes with Windows)

**Install pywin32 on Windows host:**
```bash
pip install pywin32
```

## Configuration

All configuration is done via environment variables in `docker-compose.yml`:

- `LOGIN_PASSWORD`: Password for login (from `.env`)
- `MONGODB_HOST`: MongoDB hostname (default: `mongodb`)
- `MONGODB_PORT`: MongoDB port (default: `27017`)
- `WINDOWS_COLLECTOR_HOST`: Windows collector host (default: `host.docker.internal`)
- `WINDOWS_COLLECTOR_PORT`: Windows collector port (default: `5001`)

## Features

### Filtering
- Filters apply to both charts and tables
- Filter by log name, level, provider, message, date range, and event ID
- Charts update automatically when filters are applied
- Statistics reflect filtered data

### Duplicate Prevention
- Automatic duplicate detection based on timestamp, event ID, and provider
- Prevents duplicate log entries in the database

### Charts
- **Logs by Level**: Pie chart showing distribution of log levels
- **Logs by Type**: Bar chart showing logs by log name
- **Logs Over Time**: Line chart showing log frequency over time
- All charts are responsive and stay within their containers

## Troubleshooting

**Logs not collecting?**
- Make sure Docker Desktop is running
- Ensure Python with pywin32 is installed on Windows host
- Start Windows collector: `.\start-windows-collector.ps1`
- Check that Windows collector server is running: `http://localhost:5001/health`
- Check backend logs: `docker-compose logs backend`

**MongoDB connection issues?**
- Wait for MongoDB to be healthy: `docker-compose ps`
- Check MongoDB logs: `docker-compose logs mongodb`

**Frontend not loading?**
- Check that all services are running: `docker-compose ps`
- Check backend logs: `docker-compose logs backend`

**Windows collector not starting?**
- Ensure Python is in your PATH
- Install pywin32: `pip install pywin32`
- Check if port 5001 is available
- Run manually: `python agent\windows_collector_server.py`

**Charts not updating with filters?**
- Clear browser cache
- Check browser console for errors
- Ensure filters are applied correctly

## License

MIT
