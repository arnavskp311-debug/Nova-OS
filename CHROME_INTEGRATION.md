# NOVA Browser // Google Chrome Safe Integration Guide

> **SECURITY MANDATE**: NOVA Browser operates strictly as a safe, read-only companion to Google Chrome on Windows. It **never** modifies Chrome's profile files, **never** attempts to bypass security locks, and **never** extracts, decrypts, or shares passwords, cookies, or authentication tokens.

---

## 1. Architectural Philosophy

NOVA Browser is built using **Python 3.12**, **PySide6**, and **Qt WebEngine (Chromium engine)**. It delivers a modern, tabbed cybernetic web experience inside NOVA OS while coexisting peacefully with your primary Google Chrome installation.

### Comparison: Safe Integration vs. Dangerous Hacks

| Feature / Behavior | Dangerous / Malicious Approach | NOVA Browser Safe Approach |
| :--- | :--- | :--- |
| **Passwords** | Decrypting `Login Data` via DPAPI / App-Bound Encryption hooks | ❌ **Strictly Blocked.** Passwords are never touched. Sign in separately or use "Open in Chrome". |
| **Cookies / Sessions** | Decrypting `Network/Cookies` or hijacking session tokens | ❌ **Strictly Blocked.** Sessions are isolated. NOVA has its own sandboxed profile in `data/browser_profile/`. |
| **Bookmarks** | Overwriting Chrome's JSON or injecting bookmarks directly | ✅ **Safe Read-Only Import.** Reads Chrome's `Bookmarks` JSON in read-only mode and imports copies into SQLite. Reversible with 1-click purge. |
| **History** | Querying Chrome's live database during write locks | ✅ **Safe Non-Locking Snapshot.** Copies to a temporary file before read-only querying. Never disrupts Chrome. |
| **URL Handoff** | Intercepting browser hooks or injecting DLLs | ✅ **Supported Process Spawning.** Launches `chrome.exe --profile-directory="<profile>" <url>` safely. |
| **Extensions** | Injecting scripts into Chrome's memory space | ✅ **Official Native Messaging.** Uses Chrome's documented Native Messaging host interface. |

---

## 2. Core Capabilities

### A. "Connect with Chrome" Gateway
Located directly in NOVA Browser's toolbar (`🛡️ Chrome Gateway`).
- **Connection Status**: Displays whether Chrome is detected, active profile path, and real-time connection status (`CONNECTED` or `DISCONNECTED`).
- **Explicit Consent**: Requires user to review permissions before any data reading is allowed.
- **Granular Permissions**:
  - `Allow reading Bookmarks` (Read-only)
  - `Allow reading Browsing History` (Read-only snapshot)
  - `Allow URL Handoff to Chrome`
- **Instant Disconnect**: Revokes all permissions immediately and disables integration.

### B. Safe Read-Only Bookmarks Import
- Chrome stores bookmarks in plain-text JSON:  
  `%LOCALAPPDATA%\Google\Chrome\User Data\<Profile>\Bookmarks`
- NOVA Browser parses `roots.bookmark_bar`, `roots.other`, and `roots.synced` recursively.
- Imported entries are stored in NOVA OS's SQLite database (`browser_bookmarks`) tagged with `imported_from = 'Chrome (<Profile>)'`.
- **Reversible:** Clicking **"Purge Imported Bookmarks"** deletes only the imported Chrome bookmarks without altering native NOVA bookmarks or touching Chrome.

### C. Safe Read-Only History Snapshot
- Chrome stores history in an SQLite database:  
  `%LOCALAPPDATA%\Google\Chrome\User Data\<Profile>\History`
- When Chrome is running, querying this file directly can cause lock contention (`database is locked`) or corrupt writes.
- **NOVA's Non-Locking Architecture**:
  1. Copies the file to a secure, temporary location (`tempfile.NamedTemporaryFile`).
  2. Opens the temporary copy using SQLite's read-only URI mode (`file:...mode=ro`).
  3. Queries the top recent entries (`urls` table).
  4. Stores the records in NOVA's `browser_history` table.
  5. Deletes the temporary copy immediately in a `finally` block.
- **Reversible:** Clicking **"Purge Imported History"** removes all imported entries cleanly.

### D. Bi-Directional URL Handoff
- **NOVA ➔ Chrome:**
  - Click the **"🌐 Open in Chrome"** button in the NOVA Browser navigation bar.
  - Current webpage URL is validated (must be `http://` or `https://`) and dispatched to Chrome using standard unprivileged process execution.
  - Automatically targets the active Chrome profile if configured.
- **Chrome ➔ NOVA:**
  - Launch NOVA Browser with an explicit target URL:
    ```powershell
    python main.py --url https://github.com
    ```
  - If NOVA OS is already running, entering or pasting any URL into the omnibox loads it immediately in a new or existing tab.

---

## 3. Chrome Security Disclosures & Limitations

### Why can't active logins or cookies be seamlessly shared?
Google Chrome utilizes multi-tiered security to protect user sessions:
1. **Windows DPAPI (Data Protection API):** Encrypts master keys bound to the logged-in Windows user account.
2. **App-Bound Encryption (Chrome 127+):** Binds encryption keys to Chrome's signed system process identity, specifically blocking other applications from reading saved passwords and cookie encryption keys.
3. **Cookie Sandboxing:** Web cookies often have `HttpOnly` and `SameSite` flags that prevent extraction.

**NOVA Browser strictly respects these boundaries.** Attempting to decrypt or siphon Chrome's cookies would classify an application as credential-stealing malware.

### Safe Alternatives:
1. **URL Handoff:** For websites where you are already signed into Chrome (e.g., Google Workspace, banking, GitHub), click **"Open in Chrome"**. The page opens instantly in your authenticated Chrome session.
2. **Dedicated Sign-In:** For daily browsing inside NOVA OS, sign in directly in NOVA Browser. NOVA Browser uses an isolated `QWebEngineProfile` stored in `data/browser_profile/`, keeping your cookies and sessions safely preserved inside your trial folder.

---

## 4. Official Native Messaging Architecture (Optional Extension)

Chrome's officially supported method for desktop app integration is **Native Messaging**.

### How it works:
1. An official Chrome extension (installed by the user from Chrome Web Store or in Developer Mode) requests the `"nativeMessaging"` permission.
2. The extension initiates communication via `chrome.runtime.connectNative("com.nova.os.browser.bridge")`.
3. Chrome launches the registered native messaging host executable with stdio redirection.
4. Messages are exchanged via standard input/output as JSON strings, with each message preceded by a 32-bit integer indicating byte length.

### Host Manifest (`com.nova.os.browser.bridge.json`)
```json
{
  "name": "com.nova.os.browser.bridge",
  "description": "NOVA OS Safe Chrome Companion Bridge",
  "path": "C:\\Users\\<user>\\Desktop\\Project\\O.S\\nova\\native_bridge.bat",
  "type": "stdio",
  "allowed_origins": [
    "chrome-extension://<EXTENSION_ID_HERE>/"
  ]
}
```

### Registry Registration (Current User Only — No Admin Needed):
```text
Key: HKCU\Software\Google\Chrome\NativeMessagingHosts\com.nova.os.browser.bridge
Value (Default): Path to com.nova.os.browser.bridge.json
```

---

## 5. Verification & Testing

To run the automated test suite verifying Chrome discovery, read-only bookmarks/history import, and browser tab initialization:
```powershell
python tests/test_nova.py
```
