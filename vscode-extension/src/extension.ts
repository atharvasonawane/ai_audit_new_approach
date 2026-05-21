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

        // Absolute path to the project root — normalized so backslashes are single on Windows
        const rootPath = path.normalize("C:\\Users\\Atharvaso\\Desktop\\final_approach_main");

        const workspacePath = workspaceFolders && workspaceFolders.length > 0 
            ? workspaceFolders[0].uri.fsPath 
            : rootPath;  // fall back to project root when no folder is open
        const apiServerPath = path.join(rootPath, 'report', 'api_server.py');
        const venvPythonPath = path.join(rootPath, 'audit_tool', 'venv', 'Scripts', 'python.exe');

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

        // Create Webview
        const panel = vscode.window.createWebviewPanel(
            'codeAuditLibrarian',
            'Code Audit Librarian',
            vscode.ViewColumn.One,
            {
                enableScripts: true,
                localResourceRoots: [vscode.Uri.file(path.join(rootPath, 'report', 'frontend', 'dist'))]
            }
        );

        // Listen for the 'webviewReady' handshake from Vue and respond immediately
        panel.webview.onDidReceiveMessage(
            async (message) => {
                if (message.command === 'webviewReady') {
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
                } else if (message.command === 'openFolderDialog') {
                    const uri = await vscode.window.showOpenDialog({
                        canSelectFiles: false,
                        canSelectFolders: true,
                        canSelectMany: false,
                        openLabel: 'Select Project Folder'
                    });
                    if (uri && uri[0]) {
                        panel.webview.postMessage({ type: 'selectedFolder', path: uri[0].fsPath });
                    }
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
    if (apiProcess) {
        apiProcess.kill();
    }
}
