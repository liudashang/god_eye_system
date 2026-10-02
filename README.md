# God Eye System

> 
> ⚠️ **Important License Statement: This project is Source‑Available and NOT an OSI-approved open-source project**
> 
> 
> - ✅ Allowed: For personal non-commercial scenarios, local deployment and research **without modifying source code**
> - ❌ Prohibited: Without written authorization from the copyright owner, modifying source code, creating derivative works, forking, public release or redistribution
> - ❌ Prohibited: Any commercial usage, including enterprise internal deployment, SaaS services, packaged sales, integration into commercial products
> - 💼 For commercial use, code modification or redistribution, commercial license purchase is required. Contact email: **your‑[email@example.com](mailto:email@example.com)**
> 
> 
> Please refer to the [`LICENSE`](./LICENSE) file in the repository root directory for the full legal license terms.

IT system topology, real-time monitoring & alerting, network Ping monitoring, latency and packet-loss visualization platform built with Flask + MySQL/MariaDB + ClickHouse + Grafana.

## 📋 Project Introduction

[`中文README.md`](./README_zh-CN.md)

God Eye System is an IT network visualization, monitoring and alert dashboard tool designed for operation & maintenance (O&M) scenarios. It supports dynamic rendering of IT system network topology, fully visualizing hardware assets such as servers, storage and network devices. It also integrates multi-node Ping link probing to collect latency and packet-loss metrics with anomaly alerting, and connects to Grafana for monitoring data visualization. It helps O&M engineers conduct daily inspections efficiently and quickly locate & troubleshoot network faults.

- Backend Framework: Flask
- Operational Database: MySQL8.0 / MariaDB
- Time-Series Storage: ClickHouse
- Visualization Dashboard: Grafana 13.0
- Client: Windows Ping Probe Client (watchdog auto-recovery)

## ⚠️ Prerequisites

> 
> **Linux OS only, Ubuntu Server recommended**

| Software | Version Requirement |
| --- | --- |
| Python | >=3.10 |
| Grafana | 13.0 |
| ClickHouse | Latest stable release |
| MySQL / MariaDB | MySQL8.0 or MariaDB |

## 🚀 Server-side Deployment Steps

### 1. Clone the repository

```
git clone [https://github.com/liudashang/god_eye_system.git](https://github.com/liudashang/god_eye_system.git)
cd god_eye_system
```

### 2. Create Python virtual environment

```
# Create virtual environment
python3 -m venv .venv
# Activate virtual environment
source .venv/bin/activate
```

### 3. MySQL database initialization

Log into MySQL client and run the SQL statements below to create business database and user:

```
-- Create user, allow access from any address
CREATE USER 'god_eye'@'%' IDENTIFIED BY 'godEye1234.';
-- Create business database with utf8mb4 charset
CREATE DATABASE god_eye_system_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- Grant privileges
GRANT ALL PRIVILEGES ON god_eye_system_db.* TO 'god_eye'@'%';
FLUSH PRIVILEGES;
```

### 4. Configure environment variables

Copy sample environment file to generate `.env`

```
cp .env.example .env
```

Edit `.env` and modify database configuration:

```
DATABASE_USER=god_eye
DATABASE_PASSWORD=godEye1234.
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_NAME=god_eye_system_db
# Absolute path for downloads directory inside project
DOWNLOAD_FILE_PATH=/home/super/py_project/god_eye_system/downloads
# ClickHouse config, update after database creation
CLICKHOUSE_HOST=localhost
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=
CLICKHOUSE_PORT=9000
CLICKHOUSE_DATABASE=test_db
```

### 5. Install Python dependencies

> 
> Make sure `.venv` virtual environment is activated

```
pip3 install -r requirements.txt
```

### 6. Project basic validation

Run entry script and verify no error output:

```
python3 autoapp.py
```

### 7. Flask database migration initialization

```
flask db init
flask db migrate
flask db upgrade
```

### 8. ClickHouse time-series database initialization

1. Manually create database inside ClickHouse service, example database name `test_db`

```
CREATE DATABASE test_db;
```

2. Execute all SQL statements from script `god_eye_system/ping_web_service/clickhouse_create_table.sql` to create tables
3. Confirm ClickHouse parameters in `.env` match your environment

### 9. Start main Web service

```
flask run
```

### 10. Initialize admin account

Access registration endpoint to create `admin` account, replace `my_ip` with your server IP address

```
http://<my_ip>:5000/test_register/
```

## 📊 Grafana Dashboard Configuration

> 
> Grafana version requirement: 13.0

1. Open Grafana Web UI, click `Dashboards` on the left sidebar
2. Click `New` on top right → **Import dashboard**
3. Import dashboard file from project: `ping_monitor/dashboard-grafana-ping.json`
4. Follow document `pytools/once_job/grafana配置.txt` to enable Grafana JWT authentication

## 🧩 Auxiliary Background Services Startup

> 
> All services should run inside the same virtual environment `.venv`. Run each service in separate terminal sessions.

1. **Ping Client Web Service (receives reporting data from Windows clients)**

```
cd ping_web_service
python3 app.py
```

2. **Ping Monitor Daemon (detect client status anomalies and trigger alerts)**

```
cd ping_monitor
python3 ping_monitor.py
```

3. **Alert Detection Service (latency & packet-loss alert message processing)**

```
cd pytools/apsecheduler
python3 alert_check.py
```

## 🖥️ Windows Ping Probe Client

> 
> Client runs only on Windows OS, embedded watchdog auto-restarts program on crash

1. Get client archive: `ping_client/god_ping_client.rar`
2. Extract archive on Windows
3. Double-click `启动程序.bat` to launch

## 📁 Brief Project Directory Structure

```
god_eye_system
├── ping_web_service        # Ping client reporting web service, ClickHouse table creation SQL
├── ping_monitor            # Ping status monitoring, Grafana dashboard JSON
├── pytools
│   ├── once_job            # Grafana JWT configuration documentation
│   └── apsecheduler        # Scheduled alert detection tasks
├── ping_client             # Windows ping probe client package
├── downloads               # File storage directory, absolute path set in .env
├── autoapp.py              # Main project entry validation script
├── requirements.txt        # Python dependency list
├── .env.example            # Environment variable template
```

## ⚠️ Notes

1. All Python backend services must run inside the same `.venv` virtual environment
2. Firewall ports need to be opened: Flask(5000), ClickHouse(9000), Grafana(3000), and port for Ping Web Service
3. Windows ping client must have network access to server API endpoints
4. For production environment, avoid `flask run` directly. gunicorn / uwsgi is recommended for web deployment
5. Default database passwords are only for testing. Change MySQL and ClickHouse passwords for production

> 
> This is deployment documentation for development environment. Production deployment requires process management (supervisor/systemd), Nginx reverse proxy and credential hardening.

## License

This project is source-available, **NOT open-source software**.
See [`LICENSE`](./LICENSE) in repository root for full license terms.

- Non-commercial users: Allowed to deploy and study locally without modifying source code; modification, derivative works, forking and redistribution are prohibited.
- Commercial usage, modification or redistribution requires written commercial authorization from the copyright holder.

Commercial licensing contact: Tianzhidaofeng - [liudashang@sina.com](mailto:liudashang@sina.com)

---
