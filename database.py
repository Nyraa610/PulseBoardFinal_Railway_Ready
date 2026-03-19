
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        """Initialise la connexion à la base de données Neon"""
        self.database_url = os.environ.get("DATABASE_URL")
        
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        # Correction pour Neon (certaines URLs utilisent postgres://)
        if self.database_url.startswith("postgres://"):
            self.database_url = self.database_url.replace("postgres://", "postgresql://", 1)
        
        logger.info("🔗 Connecting to Neon PostgreSQL...")
        self.init_database()
    
    def get_connection(self):
        """Créer une nouvelle connexion à la base de données"""
        try:
            conn = psycopg2.connect(
                self.database_url,
                cursor_factory=RealDictCursor,
                sslmode='require'  # Neon requiert SSL
            )
            return conn
        except Exception as e:
            logger.error(f"❌ Failed to connect to Neon: {e}")
            raise
    
    def init_database(self):
        """Initialiser les tables et données de démo"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Créer la table events
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS events (
                            id SERIAL PRIMARY KEY,
                            name VARCHAR(255) NOT NULL,
                            date DATE NOT NULL,
                            venue VARCHAR(255) NOT NULL,
                            capacity INTEGER NOT NULL,
                            tickets_sold INTEGER DEFAULT 0,
                            revenue DECIMAL(10,2) DEFAULT 0.00,
                            status VARCHAR(50) DEFAULT 'active',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # Vérifier si des données existent déjà
                    cur.execute("SELECT COUNT(*) FROM events")
                    count = cur.fetchone()['count']
                    
                    if count == 0:
                        # Insérer des données de démo
                        demo_events = [
                            ("🎵 Festival Jazz d'Été", "2024-07-15", "Parc Central", 5000, 3750, 187500.00),
                            ("🎨 Exposition Art Moderne", "2024-08-20", "Galerie Métropolitaine", 2000, 1650, 82500.00),
                            ("🏃 Marathon de la Ville", "2024-09-10", "Centre-ville", 10000, 8500, 425000.00),
                            ("🎭 Théâtre Classique", "2024-10-05", "Opéra National", 1500, 1200, 120000.00),
                            ("🎪 Cirque Fantastique", "2024-11-12", "Grand Chapiteau", 3000, 2100, 157500.00)
                        ]
                        
                        for event in demo_events:
                            cur.execute("""
                                INSERT INTO events (name, date, venue, capacity, tickets_sold, revenue)
                                VALUES (%s, %s, %s, %s, %s, %s)
                            """, event)
                        
                        logger.info("✅ Demo data inserted successfully")
                    
                    conn.commit()
                    logger.info("✅ Database initialized successfully with Neon")
        
        except Exception as e:
            logger.error(f"❌ Failed to initialize database: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Tester la connexion à la base de données"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    result = cur.fetchone()
                    return result is not None
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False
    
    def get_all_events(self) -> List[Dict[str, Any]]:
        """Récupérer tous les événements"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, name, date, venue, capacity, tickets_sold, revenue, status
                        FROM events
                        ORDER BY date
                    """)
                    events = cur.fetchall()
                    
                    # Convertir en liste de dictionnaires
                    return [dict(event) for event in events]
        
        except Exception as e:
            logger.error(f"❌ Failed to get events: {e}")
            raise
    
    def get_event(self, event_id: int) -> Optional[Dict[str, Any]]:
        """Récupérer un événement spécifique"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, name, date, venue, capacity, tickets_sold, revenue, status
                        FROM events
                        WHERE id = %s
                    """, (event_id,))
                    event = cur.fetchone()
                    
                    return dict(event) if event else None
        
        except Exception as e:
            logger.error(f"❌ Failed to get event {event_id}: {e}")
            raise
    
    def create_event(self, event_data: Dict[str, Any]) -> int:
        """Créer un nouvel événement"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO events (name, date, venue, capacity, tickets_sold, revenue)
                        VALUES (%(name)s, %(date)s, %(venue)s, %(capacity)s, %(tickets_sold)s, %(revenue)s)
                        RETURNING id
                    """, event_data)
                    
                    event_id = cur.fetchone()['id']
                    conn.commit()
                    return event_id
        
        except Exception as e:
            logger.error(f"❌ Failed to create event: {e}")
            raise
    
    def update_event(self, event_id: int, event_data: Dict[str, Any]) -> bool:
        """Mettre à jour un événement"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Construction dynamique de la requête UPDATE
                    set_clauses = []
                    values = []
                    
                    for key, value in event_data.items():
                        if key != 'id':  # Ne pas modifier l'ID
                            set_clauses.append(f"{key} = %s")
                            values.append(value)
                    
                    if not set_clauses:
                        return False
                    
                    values.append(event_id)
                    query = f"""
                        UPDATE events 
                        SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """
                    
                    cur.execute(query, values)
                    conn.commit()
                    
                    return cur.rowcount > 0
        
        except Exception as e:
            logger.error(f"❌ Failed to update event {event_id}: {e}")
            raise

# Instance globale (sera créée par main.py si possible)
db = None
try:
    db = DatabaseManager()
    logger.info("✅ Global database instance created")
except Exception as e:
    logger.warning(f"⚠️ Could not create global database instance: {e}")
