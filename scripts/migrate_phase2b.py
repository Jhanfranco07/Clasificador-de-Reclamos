"""Apply/rollback only to an operator-prepared SQLite copy, with a new backup."""
import argparse
import os
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sqlite', type=Path, required=True)
    parser.add_argument('--backup', type=Path, required=True)
    parser.add_argument('--rollback', action='store_true')
    args = parser.parse_args()
    source, backup = args.sqlite.resolve(), args.backup.resolve()
    protected = ROOT / 'data/smartclaim.db'
    if not source.is_file() or source.samefile(protected):
        parser.error('Se requiere una copia existente distinta de la base protegida')
    if backup.exists() or backup == source:
        parser.error('El backup debe ser un archivo nuevo')
    os.environ.update(PYTHON_DOTENV_DISABLED='1', DB_PROVIDER='sqlite', APP_ENV='development', DATABASE_URL='')
    with sqlite3.connect(f'{source.as_uri()}?mode=ro', uri=True) as original, sqlite3.connect(backup) as target:
        original.backup(target)
    from database import db_connection as db
    from database.migrations import phase2b
    db.DB_PATH = source
    if args.rollback:
        phase2b.rollback_sqlite()
    else:
        phase2b.apply()
    print('Migración completada sobre copia. Backup conservado.')


if __name__ == '__main__':
    main()
