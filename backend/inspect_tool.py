from sqlalchemy import create_engine, inspect
from app.core.db_utils import get_sync_database_url

def inspect_table(table_name):
    engine = create_engine(get_sync_database_url())
    inspector = inspect(engine)
    
    if not inspector.has_table(table_name):
        print(f"Table '{table_name}' does not exist.")
        return

    columns = inspector.get_columns(table_name)
    print(f"Columns in table '{table_name}':")
    for column in columns:
        print(f"  - {column['name']} ({column['type']}) - Nullable: {column['nullable']}")

if __name__ == "__main__":
    inspect_table("tool")
