"""
Database connection and vendor repository for PostgreSQL.
Connects the Python agents to the shared PostgreSQL database.
"""

import os
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import json

# Try to import psycopg2, fall back to sample data if not available
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    print("psycopg2 not installed. Using sample data.")


@dataclass
class VendorRecord:
    """Vendor record from PostgreSQL"""
    id: str
    name: str
    category: str
    description: str
    service_areas: List[str]
    pricing_min: float
    pricing_max: float
    rating: float
    total_reviews: int
    keywords: List[str]
    status: str = "ACTIVE"


class DatabaseConnection:
    """Simple PostgreSQL connection manager"""
    
    def __init__(self):
        # Use APP_DATABASE_URL if available (to avoid Chainlit data layer conflicts)
        # Fall back to DATABASE_URL for backward compatibility
        self.connection_string = os.getenv("APP_DATABASE_URL") or os.getenv("DATABASE_URL")
        if not self.connection_string:
            # Try individual params
            self.connection_params = {
                "host": os.getenv("DB_HOST", "localhost"),
                "port": os.getenv("DB_PORT", "5432"),
                "database": os.getenv("DB_NAME", "eventai"),
                "user": os.getenv("DB_USER", "postgres"),
                "password": os.getenv("DB_PASSWORD", "postgres"),
            }
        else:
            self.connection_params = None
        
        self._conn = None
    
    def get_connection(self):
        """Get or create database connection"""
        if not POSTGRES_AVAILABLE:
            return None
        
        if self._conn is None or self._conn.closed:
            try:
                if self.connection_string:
                    self._conn = psycopg2.connect(self.connection_string)
                else:
                    self._conn = psycopg2.connect(**self.connection_params)
            except Exception as e:
                print(f"Database connection failed: {e}")
                return None
        
        return self._conn
    
    def close(self):
        """Close database connection"""
        if self._conn and not self._conn.closed:
            self._conn.close()


class VendorRepository:
    """Repository for vendor data from PostgreSQL"""
    
    def __init__(self, db: DatabaseConnection = None):
        self.db = db or DatabaseConnection()
    
    def search_vendors(
        self,
        event_type: str = None,
        location: str = None,
        budget: float = None,
        keywords: List[str] = None,
        limit: int = 10
    ) -> List[VendorRecord]:
        """
        Search vendors in PostgreSQL with filters.
        Falls back to sample data if DB not available.
        """
        conn = self.db.get_connection()
        
        if conn is None:
            # Fallback to sample data
            return self._get_sample_vendors(event_type, location, budget, keywords, limit)
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Build query
                query = """
                    SELECT 
                        id::text, name, category, description,
                        service_areas, pricing_min, pricing_max,
                        rating, total_reviews, keywords, status
                    FROM vendors
                    WHERE status = 'ACTIVE'
                """
                params = []
                
                # Budget filter
                if budget:
                    query += " AND pricing_min <= %s"
                    params.append(budget)
                
                # Category/keyword filter
                if event_type:
                    query += " AND (category ILIKE %s OR %s = ANY(keywords))"
                    params.extend([f"%{event_type}%", event_type.lower()])
                
                # Location filter (search in service_areas JSONB)
                if location:
                    query += " AND service_areas::text ILIKE %s"
                    params.append(f"%{location}%")
                
                # Order by rating
                query += " ORDER BY rating DESC LIMIT %s"
                params.append(limit)
                
                cur.execute(query, params)
                rows = cur.fetchall()
                
                return [self._row_to_vendor(row) for row in rows]
                
        except Exception as e:
            print(f"Database query failed: {e}")
            return self._get_sample_vendors(event_type, location, budget, keywords, limit)
    
    def get_vendor_by_id(self, vendor_id: str) -> Optional[VendorRecord]:
        """Get a single vendor by ID"""
        conn = self.db.get_connection()
        
        if conn is None:
            return None
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        id::text, name, category, description,
                        service_areas, pricing_min, pricing_max,
                        rating, total_reviews, keywords, status
                    FROM vendors
                    WHERE id = %s
                """, [vendor_id])
                row = cur.fetchone()
                return self._row_to_vendor(row) if row else None
        except Exception as e:
            print(f"Database query failed: {e}")
            return None
    
    def _row_to_vendor(self, row: Dict[str, Any]) -> VendorRecord:
        """Convert database row to VendorRecord"""
        service_areas = row.get("service_areas") or []
        if isinstance(service_areas, str):
            service_areas = json.loads(service_areas)
        
        keywords = row.get("keywords") or []
        if isinstance(keywords, str):
            keywords = keywords.split(",")
        
        return VendorRecord(
            id=row["id"],
            name=row["name"],
            category=row.get("category") or "",
            description=row.get("description") or "",
            service_areas=service_areas,
            pricing_min=float(row.get("pricing_min") or 0),
            pricing_max=float(row.get("pricing_max") or 0),
            rating=float(row.get("rating") or 0),
            total_reviews=int(row.get("total_reviews") or 0),
            keywords=keywords,
            status=row.get("status") or "ACTIVE"
        )
    
    def _get_sample_vendors(
        self,
        event_type: str = None,
        location: str = None,
        budget: float = None,
        keywords: List[str] = None,
        limit: int = 10
    ) -> List[VendorRecord]:
        """Sample vendors when database is not available"""
        samples = [
            VendorRecord(
                id="catering_001", name="Lahore Catering Excellence", category="catering",
                description="Premium cuisine for weddings and events",
                service_areas=["Lahore", "Islamabad"], pricing_min=50000, pricing_max=500000,
                rating=4.5, total_reviews=120,
                keywords=["wedding", "mehndi", "walima", "catering", "food", "traditional"]
            ),
            VendorRecord(
                id="venue_001", name="Royal Marquee Lahore", category="venue",
                description="Luxury wedding venue with lawns and marquees",
                service_areas=["Lahore"], pricing_min=200000, pricing_max=800000,
                rating=4.8, total_reviews=85,
                keywords=["wedding", "venue", "marquee", "hall", "lawn", "mehndi"]
            ),
            VendorRecord(
                id="photo_001", name="Moments Photography", category="photography",
                description="Wedding photography and videography",
                service_areas=["Lahore", "Islamabad", "Karachi"], pricing_min=100000, pricing_max=400000,
                rating=4.7, total_reviews=200,
                keywords=["photography", "video", "drone", "wedding", "photo"]
            ),
            VendorRecord(
                id="decor_001", name="Floral Dreams Decoration", category="decoration",
                description="Event decoration and floral arrangements",
                service_areas=["Lahore", "Islamabad"], pricing_min=80000, pricing_max=350000,
                rating=4.6, total_reviews=95,
                keywords=["decoration", "flowers", "decor", "wedding", "theme"]
            ),
            VendorRecord(
                id="music_001", name="Beat Masters DJ", category="music",
                description="DJ services and live band entertainment",
                service_areas=["Lahore", "Karachi", "Islamabad"], pricing_min=40000, pricing_max=150000,
                rating=4.4, total_reviews=150,
                keywords=["dj", "music", "band", "entertainment", "sound"]
            ),
            VendorRecord(
                id="catering_002", name="Karachi BBQ House", category="catering",
                description="BBQ and street food catering for casual events",
                service_areas=["Karachi"], pricing_min=25000, pricing_max=200000,
                rating=4.3, total_reviews=75,
                keywords=["bbq", "catering", "party", "birthday", "casual"]
            ),
        ]
        
        # Apply filters
        filtered = []
        for v in samples:
            # Budget filter
            if budget and v.pricing_min > budget:
                continue
            
            # Location filter
            if location:
                location_lower = location.lower()
                if not any(location_lower in area.lower() for area in v.service_areas):
                    continue
            
            # Category/keyword filter
            if event_type:
                event_lower = event_type.lower()
                if event_lower not in v.category.lower() and event_lower not in [k.lower() for k in v.keywords]:
                    continue
            
            filtered.append(v)
        
        return filtered[:limit]


# Singleton for easy import
_db = None

def get_database() -> DatabaseConnection:
    """Get singleton database connection"""
    global _db
    if _db is None:
        _db = DatabaseConnection()
    return _db

def get_vendor_repository() -> VendorRepository:
    """Get vendor repository with database connection"""
    return VendorRepository(get_database())
