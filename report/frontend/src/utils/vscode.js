/**
 * VS Code API Singleton
 *
 * acquireVsCodeApi() can only be called ONCE per webview lifetime.
 * This module caches the result so any component can safely import
 * and call getVsCodeApi() without triggering the "called once" error.
 */

let _vscodeApi = typeof window !== 'undefined' ? window.__vscodeApi__ : null;

/**
 * Returns the cached VS Code API instance, acquiring it on first call.
 * Returns null when running outside a VS Code Webview (e.g. browser dev mode).
 */
export function getVsCodeApi() {
  if (_vscodeApi) {
    return _vscodeApi;
  }

  if (typeof window !== 'undefined' && window.__vscodeApi__) {
    _vscodeApi = window.__vscodeApi__;
    return _vscodeApi;
  }

  if (typeof acquireVsCodeApi === 'function') {
    _vscodeApi = acquireVsCodeApi();
    if (typeof window !== 'undefined') {
      window.__vscodeApi__ = _vscodeApi;
    }
  }

  return _vscodeApi;
}
