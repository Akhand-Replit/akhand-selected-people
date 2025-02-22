import os
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from psycopg2 import pool
from datetime import datetime
from typing import Optional, Dict, List, Any
import time
import streamlit as st

class Database:
    def __init__(self):
        self.connection_pool = None
        self.init_connection_pool()
        self.create_tables()  # Initialize tables right after pool creation

    def init_connection_pool(self):
        """Initialize the connection pool with retry mechanism"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if self.connection_pool is None:
                    self.connection_pool = pool.SimpleConnectionPool(
                        1, 20,
                        dbname=st.secrets["DB_NAME"],
                        user=st.secrets["DB_USER"],
                        password=st.secrets["DB_PASSWORD"],
                        host=st.secrets["DB_HOST"],
                        port=st.secrets["DB_PORT"],
                        sslmode='require'
                    )
                return
            except Exception as e:
                print(f"Attempt {attempt + 1} failed to initialize pool: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(1)

    def get_connection(self):
        """Get a connection from the pool with retry mechanism"""
        if not self.connection_pool:
            self.init_connection_pool()
        return self.connection_pool.getconn()

    def return_connection(self, conn):
        """Return a connection to the pool"""
        if self.connection_pool and conn:
            self.connection_pool.putconn(conn)

    def execute_with_retry(self, operation: callable, *args, max_retries: int = 3) -> Any:
        """Execute database operation with retry mechanism"""
        last_error = None
        for attempt in range(max_retries):
            conn = None
            try:
                conn = self.get_connection()
                with conn:  # This ensures transaction is managed properly
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        result = operation(cur, *args)
                        return result
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                last_error = e
                if conn:
                    try:
                        conn.rollback()
                    except:
                        pass
                if attempt == max_retries - 1:
                    raise last_error
                time.sleep(1)
            except Exception as e:
                if conn:
                    try:
                        conn.rollback()
                    except:
                        pass
                raise
            finally:
                if conn:
                    self.return_connection(conn)

    def create_tables(self):
        """Create database tables if they don't exist"""
        def _create_tables(cur):
            # Create persons table if not exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS persons (
                    id SERIAL PRIMARY KEY,
                    full_name VARCHAR(255) NOT NULL,
                    father_name VARCHAR(255) NOT NULL,
                    mother_name VARCHAR(255) NOT NULL,
                    dob DATE NOT NULL,
                    gender VARCHAR(50) NOT NULL,
                    nid VARCHAR(100) NOT NULL,
                    voter_no VARCHAR(100),
                    permanent_address TEXT NOT NULL,
                    present_address TEXT NOT NULL,
                    image_data JSONB DEFAULT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create contact_info table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS contact_info (
                    id SERIAL PRIMARY KEY,
                    person_id INTEGER REFERENCES persons(id) ON DELETE CASCADE,
                    type VARCHAR(50) NOT NULL,
                    value VARCHAR(255) NOT NULL
                )
            """)

            # Create documents table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    person_id INTEGER REFERENCES persons(id) ON DELETE CASCADE,
                    url TEXT NOT NULL,
                    type VARCHAR(50) NOT NULL
                )
            """)

        try:
            self.execute_with_retry(_create_tables)
            print("Database tables created successfully")
        except Exception as e:
            print(f"Error creating tables: {str(e)}")
            raise

    def add_record(self, record: Dict) -> Optional[int]:
        def _add_record(cur, record):
            # Handle image_data properly using Json
            image_data = Json(record.get('image_data')) if record.get('image_data') else None

            # Insert person
            cur.execute("""
                INSERT INTO persons (
                    full_name, father_name, mother_name, dob, gender,
                    nid, voter_no, permanent_address, present_address,
                    image_data, description, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                record['full_name'], record['father_name'], record['mother_name'],
                record['dob'], record['gender'], record['nid'],
                record.get('voter_no'), record['permanent_address'],
                record['present_address'], image_data,
                record.get('description'), datetime.now()
            ))
            person_id = cur.fetchone()['id']

            # Insert contact info
            for mobile in record.get('mobile_numbers', []):
                cur.execute(
                    "INSERT INTO contact_info (person_id, type, value) VALUES (%s, %s, %s)",
                    (person_id, 'mobile', mobile)
                )

            for whatsapp in record.get('whatsapp_numbers', []):
                cur.execute(
                    "INSERT INTO contact_info (person_id, type, value) VALUES (%s, %s, %s)",
                    (person_id, 'whatsapp', whatsapp)
                )

            for fb_link in record.get('facebook_links', []):
                cur.execute(
                    "INSERT INTO contact_info (person_id, type, value) VALUES (%s, %s, %s)",
                    (person_id, 'facebook', fb_link)
                )

            for website in record.get('website_links', []):
                cur.execute(
                    "INSERT INTO contact_info (person_id, type, value) VALUES (%s, %s, %s)",
                    (person_id, 'website', website)
                )

            # Insert PDF URLs
            for url in record.get('pdf_urls', []):
                cur.execute(
                    "INSERT INTO documents (person_id, url, type) VALUES (%s, %s, %s)",
                    (person_id, url, 'pdf')
                )

            return person_id

        try:
            return self.execute_with_retry(_add_record, record)
        except Exception as e:
            print(f"Error adding record: {str(e)}")
            return None

    def get_all_records(self) -> List[Dict]:
        """Get all records with proper error handling"""
        def _get_all_records(cur):
            cur.execute("""
                SELECT p.*, 
                    array_agg(DISTINCT CASE WHEN ci.type = 'mobile' THEN ci.value END) FILTER (WHERE ci.type = 'mobile') as mobile_numbers,
                    array_agg(DISTINCT CASE WHEN ci.type = 'whatsapp' THEN ci.value END) FILTER (WHERE ci.type = 'whatsapp') as whatsapp_numbers,
                    array_agg(DISTINCT CASE WHEN ci.type = 'facebook' THEN ci.value END) FILTER (WHERE ci.type = 'facebook') as facebook_links,
                    array_agg(DISTINCT CASE WHEN ci.type = 'website' THEN ci.value END) FILTER (WHERE ci.type = 'website') as website_links,
                    array_agg(DISTINCT d.url) FILTER (WHERE d.type = 'pdf') as pdf_urls
                FROM persons p
                LEFT JOIN contact_info ci ON p.id = ci.person_id
                LEFT JOIN documents d ON p.id = d.person_id
                GROUP BY p.id
                ORDER BY p.created_at DESC
            """)
            records = cur.fetchall()
            if not records:
                return []

            return [{
                **record,
                'mobile_numbers': list(filter(None, record['mobile_numbers'] or [])),
                'whatsapp_numbers': list(filter(None, record['whatsapp_numbers'] or [])),
                'facebook_links': list(filter(None, record['facebook_links'] or [])),
                'website_links': list(filter(None, record['website_links'] or [])),
                'pdf_urls': list(filter(None, record['pdf_urls'] or []))
            } for record in records]

        try:
            return self.execute_with_retry(_get_all_records) or []
        except Exception as e:
            print(f"Error getting all records: {str(e)}")
            return []

    def get_record(self, record_id: int) -> Optional[Dict]:
        def _get_record(cur, record_id):
            cur.execute("""
                SELECT p.*, 
                    array_agg(DISTINCT CASE WHEN ci.type = 'mobile' THEN ci.value END) FILTER (WHERE ci.type = 'mobile') as mobile_numbers,
                    array_agg(DISTINCT CASE WHEN ci.type = 'whatsapp' THEN ci.value END) FILTER (WHERE ci.type = 'whatsapp') as whatsapp_numbers,
                    array_agg(DISTINCT CASE WHEN ci.type = 'facebook' THEN ci.value END) FILTER (WHERE ci.type = 'facebook') as facebook_links,
                    array_agg(DISTINCT CASE WHEN ci.type = 'website' THEN ci.value END) FILTER (WHERE ci.type = 'website') as website_links,
                    array_agg(DISTINCT d.url) FILTER (WHERE d.type = 'pdf') as pdf_urls
                FROM persons p
                LEFT JOIN contact_info ci ON p.id = ci.person_id
                LEFT JOIN documents d ON p.id = d.person_id
                WHERE p.id = %s
                GROUP BY p.id
            """, (record_id,))
            record = cur.fetchone()
            if record:
                return {**record,
                        'mobile_numbers': list(filter(None, record['mobile_numbers'])),
                        'whatsapp_numbers': list(filter(None, record['whatsapp_numbers'])),
                        'facebook_links': list(filter(None, record['facebook_links'])),
                        'website_links': list(filter(None, record['website_links'])),
                        'pdf_urls': list(filter(None, record['pdf_urls'] or []))
                       }
            return None

        return self.execute_with_retry(_get_record, record_id)

    def update_record(self, record_id: int, updated_data: Dict) -> bool:
        def _update_record(cur, record_id, updated_data):
            # Handle image_data properly using Json
            image_data = Json(updated_data.get('image_data')) if updated_data.get('image_data') else None

            # Update person details
            cur.execute("""
                UPDATE persons SET
                    full_name = %s,
                    father_name = %s,
                    mother_name = %s,
                    dob = %s,
                    gender = %s,
                    nid = %s,
                    voter_no = %s,
                    permanent_address = %s,
                    present_address = %s,
                    image_data = %s,
                    description = %s
                WHERE id = %s
            """, (
                updated_data['full_name'],
                updated_data['father_name'],
                updated_data['mother_name'],
                updated_data['dob'],
                updated_data['gender'],
                updated_data['nid'],
                updated_data.get('voter_no'),
                updated_data['permanent_address'],
                updated_data['present_address'],
                image_data,
                updated_data.get('description'),
                record_id
            ))

            # Update contact info
            cur.execute("DELETE FROM contact_info WHERE person_id = %s", (record_id,))
            for mobile in updated_data.get('mobile_numbers', []):
                cur.execute(
                    "INSERT INTO contact_info (person_id, type, value) VALUES (%s, %s, %s)",
                    (record_id, 'mobile', mobile)
                )

            for whatsapp in updated_data.get('whatsapp_numbers', []):
                cur.execute(
                    "INSERT INTO contact_info (person_id, type, value) VALUES (%s, %s, %s)",
                    (record_id, 'whatsapp', whatsapp)
                )

            for fb_link in updated_data.get('facebook_links', []):
                cur.execute(
                    "INSERT INTO contact_info (person_id, type, value) VALUES (%s, %s, %s)",
                    (record_id, 'facebook', fb_link)
                )

            for website in updated_data.get('website_links', []):
                cur.execute(
                    "INSERT INTO contact_info (person_id, type, value) VALUES (%s, %s, %s)",
                    (record_id, 'website', website)
                )

            # Update documents
            if 'pdf_urls' in updated_data:
                cur.execute("DELETE FROM documents WHERE person_id = %s", (record_id,))
                for url in updated_data['pdf_urls']:
                    cur.execute(
                        "INSERT INTO documents (person_id, url, type) VALUES (%s, %s, %s)",
                        (record_id, url, 'pdf')
                    )

            return True

        try:
            return self.execute_with_retry(_update_record, record_id, updated_data)
        except Exception as e:
            print(f"Error updating record: {str(e)}")
            return False

    def search_records(self, query: str) -> List[Dict]:
        def _search_records(cur, query):
            cur.execute("""
                SELECT p.*, 
                    array_agg(DISTINCT CASE WHEN ci.type = 'mobile' THEN ci.value END) FILTER (WHERE ci.type = 'mobile') as mobile_numbers,
                    array_agg(DISTINCT CASE WHEN ci.type = 'whatsapp' THEN ci.value END) FILTER (WHERE ci.type = 'whatsapp') as whatsapp_numbers,
                    array_agg(DISTINCT CASE WHEN ci.type = 'facebook' THEN ci.value END) FILTER (WHERE ci.type = 'facebook') as facebook_links,
                    array_agg(DISTINCT CASE WHEN ci.type = 'website' THEN ci.value END) FILTER (WHERE ci.type = 'website') as website_links,
                    array_agg(DISTINCT d.url) FILTER (WHERE d.type = 'pdf') as pdf_urls
                FROM persons p
                LEFT JOIN contact_info ci ON p.id = ci.person_id
                LEFT JOIN documents d ON p.id = d.person_id
                WHERE p.full_name ILIKE %s
                GROUP BY p.id
                ORDER BY p.created_at DESC
            """, (f'%{query}%',))
            records = cur.fetchall()
            if not records:
                return []
            return [{**record,
                    'mobile_numbers': list(filter(None, record['mobile_numbers'] or [])),
                    'whatsapp_numbers': list(filter(None, record['whatsapp_numbers'] or [])),
                    'facebook_links': list(filter(None, record['facebook_links'] or [])),
                    'website_links': list(filter(None, record['website_links'] or [])),
                    'pdf_urls': list(filter(None, record['pdf_urls'] or []))
                   } for record in records]

        try:
            return self.execute_with_retry(_search_records, query) or []
        except Exception as e:
            print(f"Error searching records: {str(e)}")
            return []

    def delete_record(self, record_id: int) -> bool:
        """Delete a single record by ID"""
        def _delete_record(cur, record_id):
            # First delete related records from contact_info and documents
            cur.execute("DELETE FROM contact_info WHERE person_id = %s", (record_id,))
            cur.execute("DELETE FROM documents WHERE person_id = %s", (record_id,))
            # Then delete the person record
            cur.execute("DELETE FROM persons WHERE id = %s", (record_id,))
            return True

        try:
            return self.execute_with_retry(_delete_record, record_id)
        except Exception as e:
            print(f"Error deleting record: {str(e)}")
            return False

    def delete_all_records(self) -> bool:
        """Delete all records from the database"""
        def _delete_all_records(cur):
            # First delete all related records
            cur.execute("DELETE FROM contact_info")
            cur.execute("DELETE FROM documents")
            # Then delete all person records
            cur.execute("DELETE FROM persons")
            return True

        try:
            return self.execute_with_retry(_delete_all_records)
        except Exception as e:
            print(f"Error deleting all records: {str(e)}")
            return False

# Global database instance
db = Database()