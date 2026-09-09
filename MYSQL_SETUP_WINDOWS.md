# MySQL Setup Guide for Windows - Quick Start

## 🚀 Quick Installation Steps

### Step 1: Download MySQL
1. Go to: **https://dev.mysql.com/downloads/mysql/**
2. Click: **Download** next to "MySQL Community Server 8.0.x"
3. Choose: **Windows (x86, 64-bit)**
4. Click: **Download** (no login required - skip)
5. Save file to: `Downloads` folder

---

### Step 2: Run the Installer

1. Find the downloaded `.msi` file
2. **Double-click** to run installer
3. Click: **Yes** for Administrator permission
4. Click: **Next** through setup wizard

---

### Step 3: Follow MySQL Setup Wizard

| Screen | Action |
|--------|--------|
| Welcome | Click **Next** |
| License | Click **I accept** → **Next** |
| Installation Type | Choose: **Developer Default** → **Next** |
| Products | Keep defaults → **Next** |
| Installation Path | Keep default → **Next** |
| Configuration Type | Choose: **Server only** → **Next** |
| MySQL Server Config | Keep defaults (Port: 3306) → **Next** |
| Authentication Method | Choose: **MySQL 8.0 Compatible** → **Next** |
| Root Password | Enter password: **root123** (remember this!) → **Next** |
| MySQL Service | Keep default → **Next** |
| Apply Configuration | Click: **Execute** → **Finish** |
| Complete | Click: **Finish** |

---

## ✅ Verify Installation

Open **Command Prompt** and run:

```bash
mysql --version
```

**Should show:**
```
mysql  Ver 8.0.x for Windows on x86_64
```

✅ Success!

---

## 🧪 Test Connection

```bash
# Connect to MySQL
mysql -u root -p

# When prompted for password, enter: root123

# Should show:
mysql>
```

✅ **MySQL is running!**

---

## 📋 Create Your Project User

In MySQL prompt (`mysql>`), run:

```sql
-- Create project user
CREATE USER 'access_user'@'localhost' IDENTIFIED BY 'secure_password_123';

-- Grant permissions
GRANT ALL PRIVILEGES ON access_control_db.* TO 'access_user'@'localhost';

-- Create database
CREATE DATABASE access_control_db;

-- Apply changes
FLUSH PRIVILEGES;

-- Exit
EXIT;
```

---

## 🧪 Test Project User

```bash
mysql -u access_user -p access_control_db

# Enter password: secure_password_123

# Should show:
mysql>

# List tables (should be empty)
SHOW TABLES;

# Exit
EXIT;
```

✅ **Ready to run Phase 2 SQL!**

---

## 📝 Save to `.env` File

Create file: `Anomex/.env`

```
MYSQL_HOST=localhost
MYSQL_USER=access_user
MYSQL_PASSWORD=secure_password_123
MYSQL_DATABASE=access_control_db
MYSQL_PORT=3306
```

---

## 🚀 Run Phase 2 SQL

Save the SQL from LEARNING_ROADMAP.md as `sql/01_schema.sql`

Then run:

```bash
mysql -u access_user -p access_control_db < sql/01_schema.sql

# Enter password: secure_password_123

# Tables created! ✅
```

---

## 🔧 Common Issues

### Issue 1: "mysql: command not found"
```bash
# Add MySQL to PATH
# MySQL bin folder: C:\Program Files\MySQL\MySQL Server 8.0\bin
# Add this to System PATH
```

### Issue 2: "Access denied for user 'root'"
```bash
# Reinstall and use password: root123
# OR reset password (complex process - easier to reinstall)
```

### Issue 3: "Can't connect to MySQL server"
```bash
# Start MySQL service:
# Settings → Services → Look for "MySQL80" → Start

# Or in Command Prompt (as Admin):
net start MySQL80
```

### Issue 4: "Port 3306 already in use"
```bash
# MySQL already running (this is fine!)
# Just continue using it
```

---

## 📊 Useful MySQL Commands

```bash
# Connect
mysql -u access_user -p access_control_db

# List all databases
SHOW DATABASES;

# Switch database
USE access_control_db;

# List all tables
SHOW TABLES;

# Show table structure
DESCRIBE users;

# Show create statement
SHOW CREATE TABLE users;

# Exit MySQL
EXIT;
```

---

## 🎯 Summary

✅ MySQL installed  
✅ User `access_user` created  
✅ Database `access_control_db` created  
✅ Ready for Phase 2 SQL!

Proceed with running the schema from **LEARNING_ROADMAP.md** 🚀
