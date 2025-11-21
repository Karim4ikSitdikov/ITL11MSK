import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager
from config import Config


class Database:
    """Database connection manager with connection pooling"""
    
    _pool = None
    
    @classmethod
    def initialize(cls):
        """Initialize connection pool"""
        if cls._pool is None:
            cls._pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=Config.DATABASE_URL
            )
    
    @classmethod
    @contextmanager
    def get_connection(cls):
        """Get a connection from the pool"""
        if cls._pool is None:
            cls.initialize()
        
        conn = cls._pool.getconn()
        try:
            yield conn
        finally:
            cls._pool.putconn(conn)
    
    @classmethod
    @contextmanager
    def get_cursor(cls, commit=False):
        """Get a cursor with automatic transaction management"""
        with cls.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            try:
                yield cursor
                if commit:
                    conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                cursor.close()
    
    @classmethod
    def execute_query(cls, query, params=None, fetch=True, commit=False):
        """
        Execute a query and return results
        
        Args:
            query: SQL query string
            params: Query parameters
            fetch: Whether to fetch results
            commit: Whether to commit the transaction
            
        Returns:
            Query results if fetch=True, otherwise None
        """
        with cls.get_cursor(commit=commit) as cursor:
            cursor.execute(query, params or ())
            if fetch:
                # Only fetch if there are results to fetch
                if cursor.description is not None:
                    return cursor.fetchall()
                return None
            return None
    
    @classmethod
    def execute_many(cls, query, data_list):
        """
        Execute a query with multiple parameter sets
        
        Args:
            query: SQL query string
            data_list: List of parameter tuples
        """
        with cls.get_cursor(commit=True) as cursor:
            cursor.executemany(query, data_list)
    
    @classmethod
    def init_schema(cls, schema_file='database/schema.sql'):
        """Initialize database schema from SQL file"""
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(schema_sql)
            conn.commit()
            cursor.close()
        
        print("Database schema initialized successfully")
    
    @classmethod
    def close_all(cls):
        """Close all connections in the pool"""
        if cls._pool:
            cls._pool.closeall()
            cls._pool = None


def get_db():
    """Helper function to get database instance"""
    return Database


if __name__ == '__main__':
    # Test database connection
    try:
        Database.initialize()
        result = Database.execute_query("SELECT version();")
        print("Database connection successful!")
        print(f"PostgreSQL version: {result[0]['version']}")
        Database.close_all()
    except Exception as e:
        print(f"Database connection failed: {e}")
