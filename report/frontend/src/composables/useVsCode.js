let vsCodeApiCache = typeof window !== 'undefined' ? window.__vscodeApi__ : null;

/**
 * Vue 3 Composable for communicating with the VS Code extension host.
 * Implements a secure singleton pattern for acquireVsCodeApi().
 */
export function useVsCode() {
    // Initialize VS Code API if available
    if (typeof acquireVsCodeApi !== 'undefined') {
        if (vsCodeApiCache === null) {
            if (typeof window !== 'undefined' && window.__vscodeApi__) {
                vsCodeApiCache = window.__vscodeApi__;
            } else {
                vsCodeApiCache = acquireVsCodeApi();
                if (typeof window !== 'undefined') {
                    window.__vscodeApi__ = vsCodeApiCache;
                }
            }
        }
    } else {
        // Fail silently or log a clean system tracking notice when opened in standard browser
        console.log('[System Notice] VS Code API is not available. Operating in standard browser mode.');
    }

    function sendMessage(command, payload) {
        if (vsCodeApiCache) {
            vsCodeApiCache.postMessage({
                command,
                payload
            });
        } else {
            console.log(`[Browser Mode Override] Sent message: ${command}`, payload);
        }
    }

    /**
     * Requests the VS Code extension host to jump to the specified file and line.
     * Falls back to a browser trace when running outside the VS Code webview.
     * 
     * @param {string} filePath - Relative target file path
     * @param {number|string} lineNumber - 1-indexed target line number
     */
    function jumpToCode(filePath, lineNumber) {
        sendMessage('jumpToCode', {
            filePath,
            lineNumber: Number(lineNumber)
        });
    }

    return {
        sendMessage,
        jumpToCode,
        isVsCode: typeof acquireVsCodeApi !== 'undefined'
    };
}
