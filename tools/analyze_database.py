#!/usr/bin/env python3
"""
Database Analysis Tool for EAUR MIS-QuickBooks Integration

This tool analyzes the MIS database dump and generates SQLAlchemy models
automatically based on the existing schema.

Usage:
    python tools/analyze_database.py --dump-file path/to/dump.sql
    python tools/analyze_database.py --live-db --host localhost --user user --password pass --database mis_db
"""

import argparse
import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from sqlalchemy import create_engine, MetaData, inspect, text
from sqlalchemy.engine import Engine
from datetime import datetime
# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@dataclass
class ColumnInfo:
    name: str
    type: str
    nullable: bool
    default: Any
    primary_key: bool
    foreign_key: Optional[str] = None
    comment: Optional[str] = None

@dataclass
class TableInfo:
    name: str
    columns: List[ColumnInfo]
    foreign_keys: List[Dict]
    indexes: List[Dict]
    comment: Optional[str] = None

class DatabaseAnalyzer:
    """Analyzes database schema and generates SQLAlchemy models"""
    
    def __init__(self):
        self.tables: Dict[str, TableInfo] = {}
        self.relationships: Dict[str, List[str]] = {}
    
    def analyze_from_dump(self, dump_file: str) -> None:
        """Analyze database schema from SQL dump file"""
        print(f"Analyzing database dump: {dump_file}")
        
        if not os.path.exists(dump_file):
            raise FileNotFoundError(f"Dump file not found: {dump_file}")
        
        with open(dump_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Parse CREATE TABLE statements
        self._parse_create_tables(sql_content)
        
        # Parse foreign key constraints
        self._parse_foreign_keys(sql_content)
        
        print(f"Found {len(self.tables)} tables")
    
    def analyze_from_live_db(self, connection_string: str) -> None:
        """Analyze database schema from live database connection"""
        print(f"Analyzing live database...")
        
        try:
            engine = create_engine(connection_string)
            inspector = inspect(engine)
            
            for table_name in inspector.get_table_names():
                print(f"Analyzing table: {table_name}")
                
                columns = []
                for col in inspector.get_columns(table_name):
                    column_info = ColumnInfo(
                        name=col['name'],
                        type=str(col['type']),
                        nullable=col['nullable'],
                        default=col['default'],
                        primary_key=col.get('primary_key', False),
                        comment=col.get('comment')
                    )
                    columns.append(column_info)
                
                foreign_keys = inspector.get_foreign_keys(table_name)
                indexes = inspector.get_indexes(table_name)
                
                # Get table comment
                table_comment = None
                try:
                    with engine.connect() as conn:
                        result = conn.execute(text(
                            f"SELECT table_comment FROM information_schema.tables "
                            f"WHERE table_schema = DATABASE() AND table_name = '{table_name}'"
                        ))
                        row = result.fetchone()
                        if row:
                            table_comment = row[0]
                except:
                    pass
                
                self.tables[table_name] = TableInfo(
                    name=table_name,
                    columns=columns,
                    foreign_keys=foreign_keys,
                    indexes=indexes,
                    comment=table_comment
                )
            
            print(f"Found {len(self.tables)} tables")
            
        except Exception as e:
            raise Exception(f"Failed to analyze live database: {e}")
    
    def _parse_create_tables(self, sql_content: str) -> None:
        """Parse CREATE TABLE statements from SQL dump"""
        # Regex to match CREATE TABLE statements
        table_pattern = r'CREATE TABLE `?(\w+)`?\s*\((.*?)\)(?:\s*ENGINE=.*?)?;'
        
        for match in re.finditer(table_pattern, sql_content, re.DOTALL | re.IGNORECASE):
            table_name = match.group(1)
            table_definition = match.group(2)
            
            columns = self._parse_columns(table_definition)
            
            self.tables[table_name] = TableInfo(
                name=table_name,
                columns=columns,
                foreign_keys=[],
                indexes=[]
            )
    
    def _parse_columns(self, table_definition: str) -> List[ColumnInfo]:
        """Parse column definitions from CREATE TABLE statement"""
        columns = []
        
        # Split by commas, but be careful with function calls
        lines = [line.strip() for line in table_definition.split('\n') if line.strip()]
        
        for line in lines:
            line = line.rstrip(',')
            
            # Skip constraints and keys for now
            if any(keyword in line.upper() for keyword in ['PRIMARY KEY', 'FOREIGN KEY', 'KEY ', 'INDEX', 'CONSTRAINT']):
                continue
            
            # Parse column definition
            column_match = re.match(r'`?(\w+)`?\s+(\w+(?:\([^)]+\))?)\s*(.*)', line)
            if column_match:
                col_name = column_match.group(1)
                col_type = column_match.group(2)
                col_attributes = column_match.group(3).upper()
                
                nullable = 'NOT NULL' not in col_attributes
                primary_key = 'PRIMARY KEY' in col_attributes or 'AUTO_INCREMENT' in col_attributes
                default = None
                
                # Extract default value
                default_match = re.search(r"DEFAULT\s+([^,\s]+)", col_attributes)
                if default_match:
                    default = default_match.group(1).strip("'\"")
                
                columns.append(ColumnInfo(
                    name=col_name,
                    type=col_type,
                    nullable=nullable,
                    default=default,
                    primary_key=primary_key
                ))
        
        return columns
    
    def _parse_foreign_keys(self, sql_content: str) -> None:
        """Parse foreign key constraints from SQL dump"""
        # This is a simplified parser - you might need to enhance it
        fk_pattern = r'FOREIGN KEY \(`?(\w+)`?\) REFERENCES `?(\w+)`?\s*\(`?(\w+)`?\)'
        
        for match in re.finditer(fk_pattern, sql_content, re.IGNORECASE):
            # Implementation would go here
            pass
    
    def generate_models(self, output_dir: str = "application/models") -> None:
        """Generate SQLAlchemy model files"""
        print(f"Generating models in {output_dir}")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate MIS models file
        self._generate_mis_models_file(output_dir)
        
        # Generate individual model files if needed
        # self._generate_individual_model_files(output_dir)
        
        print("Model generation completed")
    
    def _generate_mis_models_file(self, output_dir: str) -> None:
        """Generate the main MIS models file"""
        file_path = os.path.join(output_dir, "mis_models1.py")
        
        with open(file_path, 'w') as f:
            f.write(self._get_file_header())
            f.write(self._get_imports())
            f.write(self._get_base_class())
            
            for table_name, table_info in self.tables.items():
                f.write(self._generate_model_class(table_info))
        
        print(f"Generated: {file_path}")
    
    def _get_file_header(self) -> str:
        """Get file header with documentation"""
        return f'''"""
MIS Database Models for EAUR MIS-QuickBooks Integration

Auto-generated from database analysis on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
These models represent the existing MIS database structure.

DO NOT MODIFY THIS FILE MANUALLY - it will be regenerated when the database schema changes.
"""

'''
    
    def _get_imports(self) -> str:
        """Get necessary imports for the models file"""
        return '''from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Decimal, ForeignKey, Text, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from application.utils.database import db_manager

# Base class for MIS models
MISBase = declarative_base()

'''
    
    def _get_base_class(self) -> str:
        """Get base model class with common functionality"""
        return '''class MISBaseModel(MISBase):
    """Base model for MIS database tables"""
    __abstract__ = True
    
    @classmethod
    def get_session(cls):
        """Get database session for MIS database"""
        return db_manager.get_mis_session()

'''
    
    def _generate_model_class(self, table_info: TableInfo) -> str:
        """Generate SQLAlchemy model class for a table, including foreign keys and relationships"""
        class_name = self._to_pascal_case(table_info.name)
        
        model = f'''class {class_name}(MISBaseModel):
        """Model for {table_info.name} table"""
        __tablename__ = '{table_info.name}'
        
    '''

        # Determine primary key column (for __repr__)
        pk_column = next((c.name for c in table_info.columns if c.primary_key), None)

        # Add columns
        for col in table_info.columns:
            col_def = f"{col.name} = Column("
            
            # SQLAlchemy type
            type_mapping = {
                'int': 'Integer',
                'bigint': 'Integer',
                'smallint': 'Integer',
                'tinyint': 'Integer',
                'varchar': 'String',
                'char': 'String',
                'text': 'Text',
                'longtext': 'Text',
                'decimal': 'Decimal',
                'float': 'Float',
                'double': 'Float',
                'datetime': 'DateTime',
                'date': 'DateTime',
                'timestamp': 'DateTime',
                'boolean': 'Boolean',
                'tinyint(1)': 'Boolean'
            }
            base_type = col.type.lower().split('(')[0]
            sqlalchemy_type = type_mapping.get(base_type, 'String')

            # Handle string length
            if 'varchar' in col.type.lower() or 'char' in col.type.lower():
                length_match = re.search(r'\((\d+)\)', col.type)
                if length_match:
                    sqlalchemy_type = f"String({length_match.group(1)})"
            
            # Handle decimal precision
            elif 'decimal' in col.type.lower():
                precision_match = re.search(r'\((\d+),(\d+)\)', col.type)
                if precision_match:
                    sqlalchemy_type = f"Decimal({precision_match.group(1)}, {precision_match.group(2)})"
            
            col_def += sqlalchemy_type

            # Add ForeignKey if available
            if col.foreign_key:
                col_def += f", ForeignKey('{col.foreign_key}')"
            
            # Constraints
            if col.primary_key:
                col_def += ", primary_key=True"
            if not col.nullable:
                col_def += ", nullable=False"
            if col.default is not None:
                if col.default.upper() == 'CURRENT_TIMESTAMP':
                    col_def += ", default=datetime.utcnow"
                else:
                    col_def += f", default='{col.default}'"

            col_def += ")"
            model += f"    {col_def}\n"

        # Add relationships
        for fk in table_info.foreign_keys:
            related_class = self._to_pascal_case(fk['referred_table'])
            rel_name = fk['column'] + "_rel"
            model += f"    {rel_name} = relationship('{related_class}', backref='{table_info.name}s')\n"

        # __repr__ method
        if pk_column:
            model += f'''
        def __repr__(self):
            return f'<{class_name} {{{{self.{pk_column}}}}}>'
    '''
        else:
            model += f'''
        def __repr__(self):
            return f'<{class_name} (no primary key)>'
    '''

        model += "\n"
        return model

    
    def _generate_column_definition(self, col: ColumnInfo) -> str:
        """Generate SQLAlchemy column definition"""
        # Map MySQL types to SQLAlchemy types
        type_mapping = {
            'int': 'Integer',
            'bigint': 'Integer',
            'smallint': 'Integer',
            'tinyint': 'Integer',
            'varchar': 'String',
            'char': 'String',
            'text': 'Text',
            'longtext': 'Text',
            'decimal': 'Decimal',
            'float': 'Float',
            'double': 'Float',
            'datetime': 'DateTime',
            'date': 'DateTime',
            'timestamp': 'DateTime',
            'boolean': 'Boolean',
            'tinyint(1)': 'Boolean'
        }
        
        # Extract base type
        base_type = col.type.lower().split('(')[0]
        sqlalchemy_type = type_mapping.get(base_type, 'String')
        
        # Handle string length
        if 'varchar' in col.type.lower() or 'char' in col.type.lower():
            length_match = re.search(r'\((\d+)\)', col.type)
            if length_match:
                sqlalchemy_type = f"String({length_match.group(1)})"
        
        # Handle decimal precision
        elif 'decimal' in col.type.lower():
            precision_match = re.search(r'\((\d+),(\d+)\)', col.type)
            if precision_match:
                sqlalchemy_type = f"Decimal({precision_match.group(1)}, {precision_match.group(2)})"
        
        # Build column definition
        col_def = f"{col.name} = Column({sqlalchemy_type}"
        
        # Add constraints
        if col.primary_key:
            col_def += ", primary_key=True"
        
        if not col.nullable:
            col_def += ", nullable=False"
        
        if col.default is not None:
            if col.default.upper() == 'CURRENT_TIMESTAMP':
                col_def += ", default=datetime.utcnow"
            else:
                col_def += f", default='{col.default}'"
        
        col_def += ")"
        
        return col_def
    
    def _to_pascal_case(self, snake_str: str) -> str:
        """Convert snake_case to PascalCase"""
        components = snake_str.split('_')
        return ''.join(x.capitalize() for x in components)
    
    def print_summary(self) -> None:
        """Print analysis summary"""
        print("\n" + "="*50)
        print("DATABASE ANALYSIS SUMMARY")
        print("="*50)
        print(f"Total tables: {len(self.tables)}")
        print("\nTables found:")
        
        for table_name, table_info in self.tables.items():
            print(f"  - {table_name} ({len(table_info.columns)} columns)")
        
        print("\nKey tables for QuickBooks integration:")
        key_tables = ['invoice', 'payments', 'personal_ug', 'campus', 'intakes', 'specialisations']
        for table in key_tables:
            if table in self.tables:
                print(f"  ✓ {table}")
            else:
                print(f"  ✗ {table} (not found)")
        
        print("\n" + "="*50)

def main():
    parser = argparse.ArgumentParser(description='Analyze MIS database and generate models')
    
    # Database source options
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument('--dump-file', help='Path to SQL dump file')
    source_group.add_argument('--live-db', action='store_true', help='Connect to live database')
    
    # Live database connection options
    parser.add_argument('--host', default='localhost', help='Database host')
    parser.add_argument('--port', type=int, default=3306, help='Database port')
    parser.add_argument('--user', help='Database user')
    parser.add_argument('--password', help='Database password')
    parser.add_argument('--database', help='Database name')
    
    # Output options
    parser.add_argument('--output-dir', default='application/models', help='Output directory for models')
    parser.add_argument('--summary-only', action='store_true', help='Only show analysis summary')
    
    args = parser.parse_args()
    
    analyzer = DatabaseAnalyzer()
    
    try:
        if args.dump_file:
            analyzer.analyze_from_dump(args.dump_file)
        else:
            # Build connection string
            if not all([args.user, args.password, args.database]):
                print("Error: --user, --password, and --database are required for live database connection")
                sys.exit(1)
            
            connection_string = f"mysql+pymysql://{args.user}:{args.password}@{args.host}:{args.port}/{args.database}"
            analyzer.analyze_from_live_db(connection_string)
        
        analyzer.print_summary()
        
        if not args.summary_only:
            analyzer.generate_models(args.output_dir)
            print(f"\nModels generated successfully in {args.output_dir}")
            print("Next steps:")
            print("1. Review the generated models")
            print("2. Add relationships between models")
            print("3. Update application/__init__.py to import the new models")
            print("4. Create and run migrations for any new fields needed")
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
