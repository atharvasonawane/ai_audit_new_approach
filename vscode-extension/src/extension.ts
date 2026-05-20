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
        if (!workspaceFolders) {
            vscode.window.showErrorMessage('Code Audit Librarian requires an open workspace.');
            return;
        }

        const workspacePath = workspaceFolders[0].uri.fsPath;

        // TODO: Replace this with the absolute path to your audit_tool folder
        const rootPath = "C:\\\\Users\\\\Atharvaso\\\\Desktop\\\\final_approach_main";
        const apiServerPath = path.join(rootPath, 'report', 'api_server.py');
        const venvPythonPath = path.join(rootPath, 'audit_tool', 'venv', 'Scripts', 'python.exe');

        // Spawn the Flask server
        try {
            apiProcess = cp.spawn(venvPythonPath, [apiServerPath, '--port', port.toString()], {
                cwd: workspacePath
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

        // Inject HTML
        const htmlContent = getWebviewContent(panel.webview, rootPath, port);
        panel.webview.html = htmlContent;

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

function getWebviewContent(webview: vscode.Webview, rootPath: string, port: number) {
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

        // Inject window.__FLASK_PORT__
        const injection = `<script>window.__FLASK_PORT__ = ${port};</script>`;
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
