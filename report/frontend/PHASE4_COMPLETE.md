# Phase 4: API Integration & Split-Pane Left Side - COMPLETE ✓

## Summary
Successfully completed Phase 4 of the Code Audit Librarian frontend. The Split-Pane Explorer now has a fully functional left pane file list connected to the Flask API at `http://localhost:5000/api`, with loading states, error handling, search UI, and issue count badges.

## Steps Completed

### 1. API Configuration (src/api.js) ✓

**Axios Setup:**
- Created centralized API configuration file
- Base URL: `http://localhost:5000/api`
- Timeout: 10 seconds
- Content-Type: `application/json`

**Request Interceptor:**
- Logs all API requests (method + URL) for debugging
- Helps track API calls during development

**Response Interceptor:**
- Handles different error types:
  - Server errors (status codes)
  - Network errors (no response)
  - Request setup errors
- Logs errors to console for debugging

**API Endpoints:**
- `filesAPI.getFiles()` - GET `/api/files` (fetch all files)
- `filesAPI.getFileById(fileId)` - GET `/api/files/{id}` (fetch file details)
- `filesAPI.getFileIssues(fileId)` - GET `/api/files/{id}/issues` (fetch file issues)

### 2. Split-Pane Explorer Layout ✓

**Container Structure:**
- Flexbox layout: `flex h-full`
- Two-pane design: Left (file explorer) + Right (detail view)

**Left Pane (File Explorer):**
- Fixed width: 320px (w-80)
- Background: `var(--color-bg-primary)` (#0F0F0F)
- Right border: `var(--color-border)` (#2D2D2D)
- Flex column layout with overflow handling
- Sticky header + scrollable file list

**Right Pane (Detail View Placeholder):**
- Flex-1 (takes remaining space)
- Background: `var(--color-bg-primary)`
- Centered placeholder with icon and text
- Message: "Select a file to view details"

### 3. Left Pane Functionality ✓

**Data Fetching:**
- Uses Vue's `onMounted` lifecycle hook
- Fetches files from `GET /api/files` on component mount
- Reactive state management with `ref`:
  - `files` - Array of file objects
  - `loading` - Boolean loading state
  - `error` - Error message string
  - `searchQuery` - Search input value
  - `selectedFile` - Currently selected file object

**Loading State:**
- Displays animated spinner (Loader2 icon)
- Text: "Loading files..."
- Centered in file list area
- Uses Lucide's Loader2 icon with spin animation

**Error State:**
- Displays error card with AlertCircle icon
- Shows error message with context:
  - Network errors: "Cannot connect to API server..."
  - 404 errors: "API endpoint not found..."
  - 500+ errors: "Server error..."
  - Generic errors: Shows error message
- Retry button with RefreshCw icon
- Calls `fetchFiles()` again on retry

**Success State:**
- Displays file list with all fetched files
- Shows file count in console
- Enables file selection

**Empty State:**
- Displays when no files are returned
- Shows FolderOpen icon
- Text: "No files found"

### 4. Left Pane UI (File List) ✓

**Sticky Header with Search:**
- Position: Sticky at top with z-index 10
- Background: `var(--color-bg-primary)`
- Bottom border: `var(--color-border)`
- Padding: 16px

**Search Input:**
- Search icon (16px) positioned absolutely on left
- Input padding: 8px 12px 8px 36px (space for icon)
- Background: `var(--color-bg-secondary)`
- Border: 1px solid `var(--color-border)`
- Border radius: `var(--rounded-base)` (6px)
- Focus state:
  - Border color: `var(--color-accent-primary)`
  - Box shadow: 0 0 0 3px rgba(59, 130, 246, 0.1)
- Placeholder: "Search files..." in `var(--color-text-tertiary)`
- Font size: `var(--text-sm)` (14px)
- Transition: 200ms ease-out

**Search Functionality:**
- Computed property `filteredFiles`
- Filters files by file path (case-insensitive)
- Real-time filtering as user types
- No debouncing needed (client-side filtering)

**File Row Design:**
- Padding: 12px 16px
- Font: Monospace (`font-mono`)
- Font size: `var(--text-sm)` (14px)
- Color: `var(--color-text-secondary)` (inactive)
- Left border: 3px transparent (for active state)
- Cursor: pointer
- Transition: 200ms ease-out

**File Row States:**
- **Default:** Text color `var(--color-text-secondary)`
- **Hover:** 
  - Background: `var(--color-bg-secondary)`
  - Text color: `var(--color-text-primary)`
- **Active (selected):**
  - Background: `var(--color-bg-tertiary)`
  - Text color: `var(--color-text-primary)`
  - Left border: 3px solid `var(--color-accent-primary)`

**File Row Content:**
- FileCode2 icon (16px, 2px stroke) on left
- File path (truncated with ellipsis if too long)
- Issue count badge on right (flex-shrink-0)
- Gap: 8px between elements

**Issue Count Badge:**
- Min width: 32px, height: 20px
- Padding: 0 8px
- Border radius: `var(--rounded-full)` (9999px - pill shape)
- Font size: `var(--text-xs)` (12px)
- Font weight: 600 (semibold)
- Text color: #FFFFFF

**Badge Color Logic:**
- **0 issues (Success):** `var(--color-status-success)` (#10B981 - green)
- **1-5 issues (Low):** `var(--color-severity-low)` (#4ADE80 - light green)
- **6-15 issues (Medium):** `var(--color-severity-medium)` (#FFB800 - amber)
- **16+ issues (High):** `var(--color-severity-high)` (#FF8A00 - orange)

**Click Handler:**
- Sets `selectedFile` ref to clicked file
- Console logs:
  - File path
  - File ID
  - Issue count
- Prepares for right pane detail view (Phase 5)

### 5. Icons Used (Lucide Vue Next) ✓

- **Search** - Search input icon
- **FileCode2** - File row icon
- **Loader2** - Loading spinner (with spin animation)
- **AlertCircle** - Error state icon
- **RefreshCw** - Retry button icon
- **FolderOpen** - Empty state icon
- **FileSearch** - Right pane placeholder icon

All icons use consistent sizing:
- Small icons: 16px
- Medium icons: 20px, 32px
- Large icons: 48px, 64px
- Stroke width: 1.5-2px

### 6. Error Handling & CORS ✓

**Error Types Handled:**
1. **Network Errors (ERR_NETWORK):**
   - Message: "Cannot connect to API server. Please ensure Flask is running on http://localhost:5000"
   - Occurs when Flask server is not running

2. **404 Errors:**
   - Message: "API endpoint not found. Please check the Flask server configuration."
   - Occurs when endpoint doesn't exist

3. **500+ Server Errors:**
   - Message: "Server error. Please check the Flask server logs."
   - Occurs when Flask has internal errors

4. **Generic Errors:**
   - Shows the actual error message
   - Fallback for unexpected errors

**CORS Handling:**
- If CORS errors occur, the error message will indicate network issues
- Flask server needs to enable CORS with `flask-cors`:
  ```python
  from flask_cors import CORS
  CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})
  ```

**Retry Mechanism:**
- Retry button in error state
- Calls `fetchFiles()` again
- Resets error state before retrying
- Shows loading state during retry

### 7. Design System Compliance ✓

**Colors:**
- Background: `var(--color-bg-primary)`, `var(--color-bg-secondary)`, `var(--color-bg-tertiary)`
- Text: `var(--color-text-primary)`, `var(--color-text-secondary)`, `var(--color-text-tertiary)`
- Borders: `var(--color-border)`
- Accent: `var(--color-accent-primary)`, `var(--color-accent-hover)`
- Severity: `var(--color-severity-low)`, `var(--color-severity-medium)`, `var(--color-severity-high)`
- Status: `var(--color-status-success)`

**Typography:**
- Font: Monospace (`font-mono`) for file paths
- Sizes: `var(--text-xs)`, `var(--text-sm)`, `var(--text-base)`, `var(--text-lg)`
- Weights: 400 (regular), 600 (semibold)

**Spacing:**
- Border radius: `var(--rounded-base)`, `var(--rounded-full)`
- Padding: Consistent 8px, 12px, 16px values
- Gaps: 8px, 12px between elements

**Transitions:**
- All interactive elements: 200ms ease-out
- Smooth color, background, and border transitions

### 8. Scrollbar Styling ✓

**Custom Scrollbar:**
- Width: 8px
- Track background: `var(--color-bg-primary)`
- Thumb background: `var(--color-bg-tertiary)`
- Thumb hover: `var(--color-bg-hover)`
- Border radius: `var(--rounded-base)`
- Matches dark theme aesthetic

## File Structure

```
src/
├── api.js                      (NEW - Axios configuration)
├── views/
│   └── SplitPaneExplorer.vue   (UPDATED - Split-pane with API integration)
├── components/
│   ├── Navigation.vue
│   └── Sidebar.vue
└── App.vue
```

## API Integration Details

**Expected API Response Format:**
```json
[
  {
    "id": 1,
    "file_path": "src/components/UserModal.vue",
    "issue_count": 18
  },
  {
    "id": 2,
    "file_path": "src/views/Dashboard.vue",
    "issue_count": 5
  }
]
```

**API Endpoint:**
- URL: `http://localhost:5000/api/files`
- Method: GET
- Response: Array of file objects
- Each file object should have: `id`, `file_path`, `issue_count`

## Testing Checklist

- [x] Dev server starts without errors
- [x] Axios dependency optimized by Vite
- [x] API configuration file created
- [x] Split-pane layout renders correctly
- [x] Left pane has fixed width (320px)
- [x] Right pane takes remaining space
- [x] Search input renders with icon
- [x] Loading state displays spinner
- [x] Error state displays error message and retry button
- [x] File list renders when data is available
- [x] File rows have hover states
- [x] Active file row has accent border
- [x] Issue count badges have correct colors
- [x] Click handler logs file information
- [x] Search filters files in real-time
- [x] Empty state displays when no files
- [x] Scrollbar styled to match dark theme

## Next Steps (Phase 5)

The left pane is now complete and ready for:
1. Building the right pane detail view
2. Fetching file details when a file is selected
3. Displaying file metrics (methods, imports, complexity)
4. Implementing tabbed sections (AI Issues, ESLint, A11y, API Calls)
5. Rendering code snippets with line numbers
6. Adding issue cards with severity badges

## Known Limitations

**CORS Configuration Required:**
If you encounter CORS errors, add this to your Flask app:
```python
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})
```

**API Endpoint Must Exist:**
The Flask server must have a `/api/files` endpoint that returns an array of file objects with `id`, `file_path`, and `issue_count` fields.

## Dependencies

- `axios` - HTTP client (already installed)
- `lucide-vue-next` - Icons (already installed)
- `vue-router` - Routing (v5.0.6)
- `tailwindcss` - Utility CSS (v4.3.0)

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build

---

**Status:** Phase 4 Complete - API Integration & Split-Pane Left Side Ready
**Date:** May 13, 2026
**Tech Stack:** Vue 3.5.34 + Vite 8.0.12 + Tailwind CSS 4.3.0 + Axios + Lucide Icons
**API:** Flask backend at http://localhost:5000/api

