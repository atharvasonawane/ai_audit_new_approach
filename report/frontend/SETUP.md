# Code Audit Librarian - Frontend Setup

## Stage 7 - Part 1: Scaffold & Layout

### What Was Done

1. **Scaffolded Vue 3 + Vite Project**
   - Created fresh Vue 3 project with Vite
   - Installed axios for API calls
   - Configured dev server to run on port 3000

2. **Cleaned Up Default Files**
   - ✅ Deleted: `src/components/HelloWorld.vue`
   - ✅ Deleted: `src/style.css`
   - ✅ Updated: `src/main.js` (removed style import)
   - ✅ Kept: `src/assets/` (for future use)

3. **Implemented Base Layout (App.vue)**
   - Left Sidebar: File Explorer with search
   - Right Main Area: Welcome screen + file detail placeholder
   - Dark theme with developer-tool aesthetic
   - Custom CSS (no external UI libraries)

4. **API Integration**
   - Fetches files from `http://localhost:5000/api/files`
   - Fetches project name from `http://localhost:5000/api/summary`
   - Loading state with spinner
   - Error state with retry button
   - Live data rendering in sidebar

### Features Implemented

#### Sidebar
- ✅ Project name display
- ✅ Search/filter files by path
- ✅ File list with badges (High/Medium/ESLint/A11y)
- ✅ Active file highlighting
- ✅ Stats footer (total files, filtered count)
- ✅ Custom scrollbar styling

#### Main Area
- ✅ Welcome screen with stats
- ✅ File selection handling
- ✅ Placeholder for detail tabs (next step)

#### Design System
- ✅ Dark theme (#0d1117 background, #161b22 sidebar)
- ✅ GitHub-inspired color palette
- ✅ System fonts (no external fonts)
- ✅ Smooth transitions and hover effects
- ✅ Responsive badges with severity colors

### How to Run

1. **Start the Flask API Server** (in separate terminal):
   ```bash
   python report/api_server.py
   ```
   Server runs on: http://localhost:5000

2. **Start the Vue Dev Server**:
   ```bash
   cd report/frontend
   npm run dev
   ```
   Frontend runs on: http://localhost:3000

3. **Open Browser**:
   Navigate to http://localhost:3000

### Expected Behavior

- Sidebar loads with all scanned files from the database
- Search box filters files in real-time
- Clicking a file shows placeholder detail view
- Badges show issue counts per file
- Welcome screen displays when no file is selected

### Next Steps (Stage 7 - Part 2)

- Implement Dashboard Overview (default view)
- Add Executive Summary card
- Add Summary Stats cards
- Add Worst Offenders table
- Add Issues by Category chart

### Next Steps (Stage 7 - Part 3)

- Implement File Detail View with 5 tabs:
  - Tab 1: Metrics
  - Tab 2: API Calls
  - Tab 3: Accessibility
  - Tab 4: ESLint Flags
  - Tab 5: AI Issues

### Troubleshooting

**Error: "Failed to connect to API server"**
- Make sure Flask API server is running on port 5000
- Check that `report/api_server.py` is running
- Verify no CORS errors in browser console

**Port 3000 already in use**
- Stop any other process using port 3000
- Or modify `vite.config.js` to use a different port

**No files showing in sidebar**
- Verify the database has data (run Stage 1-5 first)
- Check browser console for API errors
- Verify API endpoint returns data: http://localhost:5000/api/files
