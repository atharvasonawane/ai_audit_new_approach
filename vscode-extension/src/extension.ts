import * as vscode from 'vscode';
import * as cp from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

let apiProcess: cp.ChildProcess | undefined;

export function activate(context: vscode.ExtensionContext) {
    let disposable = vscode.commands.registerCommand('code-audit-librarian.open', () => {
        // Randomly assign a port between 5000 and 6000
        const port = 5000 + Math.floor(Math.random() * 1000);

        const workspaceFolders = vscode.workspace.workspaceFolders;

        // Resolve project root path (checking configuration settings first, then development path, then hardcoded workspace location)
        const config = vscode.workspace.getConfiguration('code-audit-librarian');
        const customPath = config.get<string>('enginePath');
        
        let rootPath = '';
        if (customPath && fs.existsSync(customPath) && fs.existsSync(path.join(customPath, 'report', 'api_server.py'))) {
            rootPath = path.resolve(customPath);
        } else {
            // Check if parent directory contains report/api_server.py (development mode / symlink)
            const parentPath = path.resolve(context.extensionPath, '..');
            if (fs.existsSync(path.join(parentPath, 'report', 'api_server.py'))) {
                rootPath = parentPath;
            } else {
                // Hardcoded fallback for default project location
                const hardcodedFallback = 'd:\\final_approach_main';
                if (fs.existsSync(path.join(hardcodedFallback, 'report', 'api_server.py'))) {
                    rootPath = hardcodedFallback;
                }
            }
        }

        if (!rootPath) {
            vscode.window.showErrorMessage(
                "Code Audit Librarian: Could not locate project engine files. " +
                "Please configure 'code-audit-librarian.enginePath' in your VS Code settings to point to your cloned repository."
            );
            return;
        }

        const workspacePath = workspaceFolders && workspaceFolders.length > 0
            ? workspaceFolders[0].uri.fsPath
            : rootPath;  // fall back to project root when no folder is open
        const apiServerPath = path.join(rootPath, 'report', 'api_server.py');
        const rootVenvPython = path.join(rootPath, 'venv', 'Scripts', 'python.exe');
        const innerVenvPython = path.join(rootPath, 'audit_tool', 'venv', 'Scripts', 'python.exe');
        const venvPythonPath = fs.existsSync(rootVenvPython) ? rootVenvPython : innerVenvPython;

        // Spawn the Flask server
        try {
            apiProcess = cp.spawn(venvPythonPath, [apiServerPath, '--port', port.toString()], {
                cwd: workspacePath || rootPath
            });

            apiProcess.stdout?.on('data', (data) => console.log(`Flask: ${data}`));
            apiProcess.stderr?.on('data', (data) => console.error(`Flask Error: ${data}`));
        } catch (err) {
            vscode.window.showErrorMessage(`Failed to start Flask server: ${err}`);
            return;
        }

        // Create Webview — dashboard lives in column 2 always
        const panel = vscode.window.createWebviewPanel(
            'codeAuditLibrarian',
            'Code Audit Librarian',
            vscode.ViewColumn.Two,
            {
                enableScripts: true,
                localResourceRoots: [vscode.Uri.file(path.join(rootPath, 'report', 'frontend', 'dist'))],
                retainContextWhenHidden: true
            }
        );

        // Central message router — all Webview→Extension communication goes here.
        panel.webview.onDidReceiveMessage(
            async (message: { command: string; payload?: Record<string, unknown> }) => {
                console.log('[CAL Webview Message received]', message);
                switch (message.command) {
                    case 'webviewReady': {
                        const folders = vscode.workspace.workspaceFolders;
                        const dynamicPath = folders && folders.length > 0
                            ? folders[0].uri.fsPath
                            : rootPath;  // fall back to project root when no folder is open
                        console.log('Code Audit Librarian: Retrieved workspace path dynamically:', dynamicPath);
                        // Pong: send the canonical 'setWorkspacePath' command the Vue app listens for
                        panel.webview.postMessage({ command: 'setWorkspacePath', path: dynamicPath });
                        // Also send legacy 'setPath' for any other components that may still listen for it
                        panel.webview.postMessage({ command: 'setPath', payload: dynamicPath });
                        console.log('Code Audit Librarian: Sent setWorkspacePath pong to Webview.');
                        console.log('Code Audit Librarian: dynamicPath value:', JSON.stringify(dynamicPath));
                        break;
                    }
                    case 'openFolderDialog': {
                        const uri = await vscode.window.showOpenDialog({
                            canSelectFiles: false,
                            canSelectFolders: true,
                            canSelectMany: false,
                            openLabel: 'Select Project Folder'
                        });
                        if (uri && uri[0]) {
                            panel.webview.postMessage({ type: 'selectedFolder', path: uri[0].fsPath });
                        }
                        break;
                    }
                    case 'jumpToCode': {
                        if (message.payload) {
                            await handleJumpToCode(message.payload);
                        }
                        break;
                    }
                    // Future commands slot in here:
                    // case 'applyAiFix': { await handleApplyAiFix(message.payload); break; }
                    // case 'rejectFix':  { await handleRejectFix(message.payload);  break; }

                    default:
                        console.warn(`[CodeAuditLibrarian] Unknown command: ${message.command}`);
                }
            },
            null,
            context.subscriptions
        );

        // Inject HTML (triggers webview execution and messages)
        const htmlContent = getWebviewContent(panel.webview, rootPath, port, workspacePath);
        panel.webview.html = htmlContent;

        // Also re-send on visibility change (e.g. user switches tabs and comes back)
        panel.onDidChangeViewState(() => {
            if (panel.visible) {
                const folders = vscode.workspace.workspaceFolders;
                const dynamicPath = folders && folders.length > 0 ? folders[0].uri.fsPath : "";
                panel.webview.postMessage({ command: 'setPath', payload: dynamicPath });
            }
        }, null, context.subscriptions);

        // Cleanup when the webview is closed
        panel.onDidDispose(() => {
            if (apiProcess) {
                apiProcess.kill();
                apiProcess = undefined;
            }
        });
    });

    context.subscriptions.push(disposable);
}

function getWebviewContent(webview: vscode.Webview, rootPath: string, port: number, workspacePath: string) {
    const distPath = path.join(rootPath, 'report', 'frontend', 'dist');
    const indexHtmlPath = path.join(distPath, 'index.html');

    let html = '';
    try {
        html = fs.readFileSync(indexHtmlPath, 'utf8');

        // Replace absolute/relative paths to assets with webview URIs
        html = html.replace(/(href|src)="\/([^"]+)"/g, (match, attr, relPath) => {
            const fileUri = vscode.Uri.file(path.join(distPath, relPath));
            const webviewUri = webview.asWebviewUri(fileUri);
            return `${attr}="${webviewUri}"`;
        });

        html = html.replace(/(href|src)="(assets\/[^"]+)"/g, (match, attr, relPath) => {
            const fileUri = vscode.Uri.file(path.join(distPath, relPath));
            const webviewUri = webview.asWebviewUri(fileUri);
            return `${attr}="${webviewUri}"`;
        });

        // Inject window.__FLASK_PORT__ and window.__WORKSPACE_PATH__
        const escapedWorkspacePath = workspacePath.replace(/\\/g, '\\\\');
        const injection = `<script>window.__FLASK_PORT__ = ${port}; window.__WORKSPACE_PATH__ = "${escapedWorkspacePath}";</script>`;
        html = html.replace('</head>', `${injection}\n</head>`);
    } catch (e) {
        html = `<!DOCTYPE html><html><body><h1>Error loading UI</h1><p>Ensure the Vue app is built at report/frontend/dist.</p><p>${e}</p></body></html>`;
    }

    return html;
}

export function deactivate() {
    if (highlightDecoration) {
        highlightDecoration.dispose();
    }
    if (apiProcess) {
        apiProcess.kill();
    }
}

// Module-level decoration tracking variable to prevent memory leaks and ghost highlights
let highlightDecoration: vscode.TextEditorDecorationType | undefined;

/**
 * Standalone helper to handle jumping to a specific file and line inside the VS Code editor.
 */
async function handleJumpToCode(payload: Record<string, unknown>): Promise<void> {
    console.log('[CAL handleJumpToCode received]', payload);
    const filePath = payload.filePath as string;
    const lineNumber = payload.lineNumber as number;

    const fileUri = resolveFileUri(filePath);
    console.log('[CAL resolved URI]', fileUri ? fileUri.toString() : 'null');
    if (!fileUri) {
        return; // resolveFileUri already showed warning/error message
    }

    try {
        const doc = await vscode.workspace.openTextDocument(fileUri);
        const line = Math.max(0, (lineNumber || 1) - 1); // DB is 1-indexed, VS Code is 0-indexed
        const range = new vscode.Range(line, 0, line, 0);

        await vscode.window.showTextDocument(doc, {
            viewColumn: vscode.ViewColumn.One, // file opens in column 1, dashboard stays in column 2
            selection: range,
            preserveFocus: false,
        });

        highlightLine(doc, line);
    } catch (err) {
        vscode.window.showErrorMessage(`Could not open: ${filePath}`);
    }
}

/**
 * Collects the names of all immediate subdirectories inside a given directory.
 * Returns an empty array if the directory cannot be read (permission errors, etc.).
 */
function collectSubdirectories(dirPath: string): string[] {
    try {
        return fs.readdirSync(dirPath, { withFileTypes: true })
            .filter(entry => entry.isDirectory())
            .map(entry => entry.name);
    } catch {
        return [];
    }
}

/**
 * Resolves a DB-stored relative file path to an absolute vscode.Uri by walking through
 * a multi-tier fallback chain.
 *
 * Resolution order:
 *  A  — Direct join:          workspaceRoot + relativePath
 *  B  — Prefix strip (×N):    workspaceRoot + relativePath with leading N segments removed
 *  C  — Subdir walk:          workspaceRoot/<subdir> + relativePath (1-level deep subfolders)
 *  D  — Subdir + prefix strip: workspaceRoot/<subdir> + relativePath with leading N segments removed
 *  E  — Basename fallback:    workspaceRoot + filename only (last resort fuzzy lookup)
 *
 * If all strategies fail, shows a diagnostic error toast with the exact Strategy-A
 * absolute path so the developer can immediately identify the directory layout mismatch.
 */
function resolveFileUri(relativePath: string): vscode.Uri | undefined {
    // ── Guard: require at least one open workspace folder ──────────────────────
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders || workspaceFolders.length === 0) {
        vscode.window.showErrorMessage(
            'No workspace folder is open. Open your project folder in VS Code to use Jump-to-Code.'
        );
        return undefined;
    }

    const workspaceRoot = workspaceFolders[0].uri.fsPath;
    console.log('[CAL ResolveFileUri] relativePath:', relativePath, 'workspaceRoot:', workspaceRoot);

    // ── Step 1: Normalize incoming path to OS-native separators ────────────────
    // Database stores paths with forward slashes; Windows needs backslashes.
    const normalizedRelative = path.normalize(relativePath.replace(/\//g, path.sep));

    // Pre-split into segments for prefix-stripping strategies
    const segments = normalizedRelative.split(path.sep).filter(s => s.length > 0);
    const baseName = path.basename(normalizedRelative);

    // ── Strategy A: Direct join ────────────────────────────────────────────────
    // workspaceRoot + relativePath  (e.g. C:\...\Project + app\src\...\File.vue)
    const strategyAPath = path.join(workspaceRoot, normalizedRelative);
    if (fs.existsSync(strategyAPath)) {
        console.log(`[CAL] resolveFileUri ✓ Strategy A: ${strategyAPath}`);
        return vscode.Uri.file(strategyAPath);
    }

    // ── Strategy B: Iterative prefix stripping ────────────────────────────────
    // Tries removing 1, 2, … (N-1) leading segments from the DB path and joining
    // with workspaceRoot. Handles cases like:
    //   DB stores  "app/src/…/File.vue"  but workspace root already contains "src/…"
    for (let strip = 1; strip < segments.length; strip++) {
        const stripped = segments.slice(strip).join(path.sep);
        const candidate = path.join(workspaceRoot, stripped);
        if (fs.existsSync(candidate)) {
            console.log(`[CAL] resolveFileUri ✓ Strategy B (strip=${strip}): ${candidate}`);
            return vscode.Uri.file(candidate);
        }
    }

    // ── Strategy C: Immediate subdirectory walk ────────────────────────────────
    // The workspace root may be a "parent" project folder and the actual code lives
    // inside a subdirectory such as "client/", "frontend/", "src/", etc.
    // Example: workspaceRoot = C:\…\StudentManagement\StudentManagement
    //          actual file   = …\StudentManagement\client\app\src\…\File.vue
    const immediateSubdirs = collectSubdirectories(workspaceRoot);
    for (const subdir of immediateSubdirs) {
        const subdirRoot = path.join(workspaceRoot, subdir);
        const candidate = path.join(subdirRoot, normalizedRelative);
        if (fs.existsSync(candidate)) {
            console.log(`[CAL] resolveFileUri ✓ Strategy C (subdir=${subdir}): ${candidate}`);
            return vscode.Uri.file(candidate);
        }
    }

    // ── Strategy D: Subdirectory walk + prefix stripping ─────────────────────
    // Combines C and B: walks into each immediate subdir AND tries stripping leading
    // path segments from the DB path.
    // Example: workspaceRoot/client + src/…/File.vue  (strips "app" prefix)
    for (const subdir of immediateSubdirs) {
        const subdirRoot = path.join(workspaceRoot, subdir);
        for (let strip = 1; strip < segments.length; strip++) {
            const stripped = segments.slice(strip).join(path.sep);
            const candidate = path.join(subdirRoot, stripped);
            if (fs.existsSync(candidate)) {
                console.log(`[CAL] resolveFileUri ✓ Strategy D (subdir=${subdir}, strip=${strip}): ${candidate}`);
                return vscode.Uri.file(candidate);
            }
        }
    }

    // ── Strategy E: Basename-only fuzzy fallback ──────────────────────────────
    // Last resort — join just the filename with workspaceRoot in case the file
    // lives directly at the project root level.
    const strategyEPath = path.join(workspaceRoot, baseName);
    if (fs.existsSync(strategyEPath)) {
        console.log(`[CAL] resolveFileUri ✓ Strategy E (basename): ${strategyEPath}`);
        return vscode.Uri.file(strategyEPath);
    }

    // ── Total failure — diagnostic toast ─────────────────────────────────────
    // Surface the exact Strategy-A path so the developer can immediately see
    // the directory-layout mismatch in the VS Code notification popup.
    console.error(`[CAL] resolveFileUri ✗ All strategies exhausted for: "${relativePath}"`);
    console.error(`[CAL]   Strategy A checked: ${strategyAPath}`);
    console.error(`[CAL]   Workspace root    : ${workspaceRoot}`);
    vscode.window.showErrorMessage(
        `File not found at: ${strategyAPath}` +
        `\n\nWorkspace root: ${workspaceRoot}` +
        `\nDB path queried: ${relativePath}` +
        `\n\nMake sure the open workspace folder matches the audited project root.`
    );
    return undefined;
}

/**
 * Temporarily highlights a target line using editor.findMatchHighlightBackground.
 */
function highlightLine(doc: vscode.TextDocument, zeroIndexedLine: number): void {
    // Dispose any previous highlight before creating a new one
    if (highlightDecoration) {
        highlightDecoration.dispose();
    }

    highlightDecoration = vscode.window.createTextEditorDecorationType({
        backgroundColor: new vscode.ThemeColor('editor.findMatchHighlightBackground'),
        isWholeLine: true,
    });

    const editor = vscode.window.visibleTextEditors.find(
        e => e.document.uri.fsPath === doc.uri.fsPath
    );
    if (!editor) {
        return;
    }

    const range = new vscode.Range(zeroIndexedLine, 0, zeroIndexedLine, 0);
    editor.setDecorations(highlightDecoration, [range]);

    setTimeout(() => {
        highlightDecoration?.dispose();
        highlightDecoration = undefined;
    }, 2000);
}
