# services/vector_retrieval.py
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

class PlaceVectorDatabase:
    """
    Use FAISS (Facebook's similarity search) to find places
    Based on TripSync AI's architecture[citation:4]
    """
    
    def __init__(self):
        # Load pre-trained embedding model (free, works for any place)
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = None
        self.places = []
        
    def build_index_from_osm(self, lat, lon, radius_km=20):
        """
        Dynamically build a vector index of places from OpenStreetMap
        This works for ANY destination, no static data needed
        """
        # Query OpenStreetMap for places
        import overpy
        api = overpy.Overpass()
        
        # Get all POIs in the area (restaurants, attractions, cafes, etc.)
        query = f"""
        [out:json];
        (
          node["tourism"](around:{radius_km*1000},{lat},{lon});
          node["amenity"](around:{radius_km*1000},{lat},{lon});
          node["leisure"](around:{radius_km*1000},{lat},{lon});
          way["tourism"](around:{radius_km*1000},{lat},{lon});
        );
        out center;
        """
        
        result = api.query(query)
        
        for node in result.nodes:
            place_data = {
                'name': node.tags.get('name', ''),
                'type': self._get_place_type(node.tags),
                'lat': node.lat,
                'lon': node.lon,
                'tags': dict(node.tags),
                'description': node.tags.get('description', '')
            }
            if place_data['name']:
                self.places.append(place_data)
        
        # Create embeddings for all places
        texts = [f"{p['name']} {p['type']} {' '.join(p['tags'].values())}" for p in self.places]
        embeddings = self.encoder.encode(texts)
        
        # Build FAISS index for fast similarity search
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings.astype('float32'))
        
        return len(self.places)
    
    def find_similar_places(self, interest_query, top_k=10):
        """Find places matching user's interest using semantic search"""
        query_embedding = self.encoder.encode([interest_query])
        distances, indices = self.index.search(query_embedding.astype('float32'), top_k)
        
        return [self.places[i] for i in indices[0]]
    
    def _get_place_type(self, tags):
        """Categorize place from OSM tags"""
        if 'amenity' in tags:
            return tags['amenity']
        elif 'tourism' in tags:
            return tags['tourism']
        elif 'leisure' in tags:
            return tags['leisure']
        return 'attraction'