/* Stand-in for Windows' winsqlite3.dll so CodeZeno's tests load under Wine.
   Every call fails with SQLITE_ERROR (1); the theme tests never use SQLite. */
#define API __declspec(dllexport) __stdcall
API int sqlite3_open_v2(const char *f, void **db, int flags, const char *vfs) { if (db) *db = 0; return 1; }
API int sqlite3_close(void *db) { return 0; }
API int sqlite3_busy_timeout(void *db, int ms) { return 1; }
API int sqlite3_exec(void *db, const char *sql, void *cb, void *arg, char **err) { return 1; }
API int sqlite3_prepare_v2(void *db, const char *sql, int n, void **stmt, const char **tail) { if (stmt) *stmt = 0; return 1; }
API int sqlite3_bind_text(void *stmt, int i, const char *t, int n, void *d) { return 1; }
API int sqlite3_step(void *stmt) { return 1; }
API int sqlite3_finalize(void *stmt) { return 0; }
API int sqlite3_column_bytes(void *stmt, int i) { return 0; }
API const unsigned char *sqlite3_column_text(void *stmt, int i) { return 0; }
API const char *sqlite3_errmsg(void *db) { return "winsqlite3 stub"; }
