# Stage 7 - Part 1: Command Reference

## Exact Terminal Commands Used

### 1. Scaffold Vue 3 + Vite Project
```bash
cd report
npm create vite@latest frontend -- --template vue
```
**What it does:** Creates a new Vue 3 project with Vite in the `report/frontend` directory

---

### 2. Install Axios
```bash
cd report/frontend
npm install axios
```
**What it does:** Installs axios HTTP client for API calls

---

### 3. Start Development Servers

#### Terminal 1 - Flask API Server
```bash
python report/api_server.py
```
**Runs on:** http://localhost:5000

#### Terminal 2 - Vue Frontend
```bash
cd report/frontend
npm run dev
```
**Runs on:** http://localhost:3000

---

## Files to Delete (Cleanup)

### Delete These Files:
```bash
# From report/frontend/src/
rm src/components/HelloWorld.vue
rm src/style.css
```

**Why:**
- `HelloWorld.vue` - Default demo component (not needed)
- `style.css` - Default styles (we use custom CSS in App.vue)

---

## Files Modified

### 1. `src/main.js`
**Before:**
```javascript
import { createApp } from 'vue'
import './style.css'  // ← Remove this line
import App from './App.vue'

createApp(App).mount('#app')
```

**After:**
```javascript
import { createApp } from 'vue'
import App from './App.vue'

createApp(App).mount('#app')
```

---

### 2. `vite.config.js`
**Before:**
```javascript
export default defineConfig({
  plugins: [vue()],
})
```

**After:**
```javascript
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    strictPort: true,
  },
})
```

---

## Files Created

### 1. `src/App.vue` (600+ lines)
- Complete layout with sidebar and main area
- Dark theme CSS
- API integration with axios
- Loading and error states
- Search/filter functionality

### 2. `SETUP.md`
- Setup instructions
- Troubleshooting guide
- Feature list

### 3. `STAGE7_PART1_COMPLETE.md`
- Detailed completion report
- Verification checklist
- Next steps

---

## Quick Start (From Scratch)

If you need to recreate this setup:

```bash
# 1. Create project
cd report
npm create vite@latest frontend -- --template vue

# 2. Install dependencies
cd frontend
npm install axios

# 3. Delete default files
rm src/components/HelloWorld.vue
rm src/style.css

# 4. Update main.js (remove style.css import)
# 5. Update vite.config.js (add port 3000)
# 6. Replace src/App.vue with our custom version

# 7. Start servers
# Terminal 1:
python report/api_server.py

# Terminal 2:
cd report/frontend
npm run dev

# 8. Open browser
# http://localhost:3000
```

---

## Verification Commands

### Check if servers are running:
```bash
# Check Flask API
curl http://localhost:5000/api/health

# Check Vue frontend (in browser)
# Navigate to http://localhost:3000
```

### Check API data:
```bash
# Get files list
curl http://localhost:5000/api/files

# Get project summary
curl http://localhost:5000/api/summary
```

---

## Stop Servers

### Stop Flask API:
```
Ctrl+C in Terminal 1
```

### Stop Vue Frontend:
```
Ctrl+C in Terminal 2
```

---

## Rebuild/Reinstall

### If you need to reinstall dependencies:
```bash
cd report/frontend
rm -rf node_modules
rm package-lock.json
npm install
```

### If you need to clear Vite cache:
```bash
cd report/frontend
rm -rf node_modules/.vite
npm run dev
```

---

## Common Issues

### Port 3000 already in use:
```bash
# Find and kill process on port 3000 (Windows)
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Or change port in vite.config.js
```

### Port 5000 already in use:
```bash
# Find and kill process on port 5000 (Windows)
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### CORS errors:
- Make sure Flask API has `flask-cors` installed
- Check that API server is running on port 5000
- Verify no browser extensions blocking CORS

### API connection failed:
```bash
# Verify Flask API is running
curl http://localhost:5000/api/health

# Check if database exists
ls audit_history.db

# Restart Flask API
python report/api_server.py
```

---

## Package.json Scripts

```json
{
  "scripts": {
    "dev": "vite",              // Start dev server
    "build": "vite build",      // Build for production
    "preview": "vite preview"   // Preview production build
  }
}
```

---

## Dependencies Installed

```json
{
  "dependencies": {
    "vue": "^3.5.13",
    "axios": "^1.7.9"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.2.1",
    "vite": "^8.0.12"
  }
}
```

---

## Project Structure After Setup

```
report/
├── api_server.py              # Flask API
└── frontend/                  # Vue.js SPA
    ├── node_modules/          # Dependencies (auto-generated)
    ├── public/                # Static files
    ├── src/
    │   ├── assets/            # Images, fonts (empty)
    │   ├── components/        # Vue components (empty)
    │   ├── App.vue           # ✅ Main component
    │   └── main.js           # ✅ Entry point
    ├── .gitignore
    ├── index.html
    ├── package.json
    ├── package-lock.json
    ├── vite.config.js        # ✅ Port 3000
    ├── SETUP.md              # ✅ Setup guide
    ├── COMMANDS_REFERENCE.md # ✅ This file
    └── STAGE7_PART1_COMPLETE.md
```

---

## Environment Requirements

- Node.js 18+ (for Vite)
- npm 9+ (comes with Node.js)
- Python 3.10+ (for Flask API)
- Modern browser (Chrome, Firefox, Edge)

---

## All Commands Summary

```bash
# Setup
cd report
npm create vite@latest frontend -- --template vue
cd frontend
npm install axios

# Cleanup
rm src/components/HelloWorld.vue
rm src/style.css

# Run
python report/api_server.py  # Terminal 1
cd report/frontend && npm run dev  # Terminal 2

# Access
# http://localhost:3000 (Frontend)
# http://localhost:5000 (API)
```

---

**That's it! Stage 7 - Part 1 is complete.** 🚀
