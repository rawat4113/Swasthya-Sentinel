"""Shared staging/commit workflow documentation helpers.
The transaction coordinator and API authorization boundary are implemented in app.main.
"""
def import_status(imported_rows, rejected_rows):
    if imported_rows and rejected_rows: return 'partially_committed'
    if imported_rows: return 'committed'
    return 'rejected'
