"""Smart playlist generation algorithms inspired by gtkpod.

This module implements dynamic playlist generation using algorithms
adapted from gtkpod's playlist management features.
"""

import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import random

from .repositories import Track, Playlist, Repository

logger = logging.getLogger(__name__)


class SmartPlaylistGenerator:
    """Generate dynamic playlists using gtkpod-inspired algorithms."""
    
    def __init__(self, track_repository: Repository):
        self.tracks = track_repository
    
    async def generate_category_playlists(self, category_field: str, 
                                        min_tracks: int = 3) -> List[Playlist]:
        """Generate playlists grouped by category (genre, artist, album)."""
        all_tracks = await self.tracks.get_tracks()
        tracks_by_category = defaultdict(list)
        
        # Group tracks by the specified field
        for track in all_tracks:
            category_value = getattr(track, category_field, None)
            if category_value:
                tracks_by_category[category_value].append(track)
        
        playlists = []
        for category_value, tracks in tracks_by_category.items():
            if len(tracks) >= min_tracks:
                playlist_id = f"auto_{category_field}_{self._safe_filename(category_value)}"
                playlist = Playlist(
                    id=playlist_id,
                    name=f"{category_field.title()}: {category_value}",
                    track_ids=[track.id for track in tracks],
                    date_created=datetime.now(),
                    is_smart=True,
                    smart_criteria={
                        'type': 'category',
                        'field': category_field,
                        'value': category_value
                    }
                )
                playlists.append(playlist)
        
        logger.info(f"Generated {len(playlists)} {category_field} playlists")
        return playlists
    
    async def generate_smart_playlists(self) -> List[Playlist]:
        """Generate comprehensive smart playlists like gtkpod."""
        playlists = []
        all_tracks = await self.tracks.get_tracks()
        
        if not all_tracks:
            logger.warning("No tracks available for smart playlist generation")
            return playlists
        
        # Most played tracks
        most_played = await self._get_most_played_tracks(all_tracks, min_count=5, limit=50)
        if most_played:
            playlists.append(Playlist(
                id="auto_most_played",
                name="Most Played",
                track_ids=[track.id for track in most_played],
                date_created=datetime.now(),
                is_smart=True,
                smart_criteria={'type': 'most_played', 'min_count': 5, 'limit': 50}
            ))
        
        # Recently added
        recent = await self._get_recently_added_tracks(all_tracks, days=30, limit=100)
        if recent:
            playlists.append(Playlist(
                id="auto_recently_added",
                name="Recently Added",
                track_ids=[track.id for track in recent],
                date_created=datetime.now(),
                is_smart=True,
                smart_criteria={'type': 'recently_added', 'days': 30, 'limit': 100}
            ))
        
        # Never played
        never_played = await self._get_never_played_tracks(all_tracks, limit=100)
        if never_played:
            playlists.append(Playlist(
                id="auto_never_played",
                name="Never Played",
                track_ids=[track.id for track in never_played],
                date_created=datetime.now(),
                is_smart=True,
                smart_criteria={'type': 'never_played', 'limit': 100}
            ))
        
        # Highly rated tracks
        highly_rated = await self._get_highly_rated_tracks(all_tracks, min_rating=4, limit=50)
        if highly_rated:
            playlists.append(Playlist(
                id="auto_highly_rated",
                name="Highly Rated",
                track_ids=[track.id for track in highly_rated],
                date_created=datetime.now(),
                is_smart=True,
                smart_criteria={'type': 'highly_rated', 'min_rating': 4, 'limit': 50}
            ))
        
        # Recently played
        recently_played = await self._get_recently_played_tracks(all_tracks, days=7, limit=50)
        if recently_played:
            playlists.append(Playlist(
                id="auto_recently_played",
                name="Recently Played",
                track_ids=[track.id for track in recently_played],
                date_created=datetime.now(),
                is_smart=True,
                smart_criteria={'type': 'recently_played', 'days': 7, 'limit': 50}
            ))
        
        logger.info(f"Generated {len(playlists)} smart playlists")
        return playlists
    
    async def generate_random_playlist(self, limit: int = 25, 
                                     filters: Optional[Dict[str, Any]] = None) -> Playlist:
        """Generate a random playlist with optional filters."""
        all_tracks = await self.tracks.get_tracks()
        
        # Apply filters if provided
        if filters:
            filtered_tracks = []
            for track in all_tracks:
                include_track = True
                
                # Filter by genre
                if 'genre' in filters and track.genre != filters['genre']:
                    include_track = False
                
                # Filter by rating
                if 'min_rating' in filters and track.rating < filters['min_rating']:
                    include_track = False
                
                # Filter by category
                if 'category' in filters and track.category != filters['category']:
                    include_track = False
                
                # Filter by play count
                if 'min_play_count' in filters and track.play_count < filters['min_play_count']:
                    include_track = False
                
                if include_track:
                    filtered_tracks.append(track)
            
            all_tracks = filtered_tracks
        
        # Randomly select tracks
        if len(all_tracks) > limit:
            selected_tracks = random.sample(all_tracks, limit)
        else:
            selected_tracks = all_tracks
        
        # Shuffle for good measure
        random.shuffle(selected_tracks)
        
        return Playlist(
            id="auto_random",
            name="Random Mix",
            track_ids=[track.id for track in selected_tracks],
            date_created=datetime.now(),
            is_smart=True,
            smart_criteria={'type': 'random', 'limit': limit, 'filters': filters}
        )
    
    async def generate_discovery_playlist(self, limit: int = 30) -> Playlist:
        """Generate a discovery playlist with variety and underplayed tracks."""
        all_tracks = await self.tracks.get_tracks()
        
        # Prefer tracks with low play counts
        underplayed = [track for track in all_tracks if track.play_count <= 2]
        
        # If we don't have enough underplayed tracks, include some regular tracks
        if len(underplayed) < limit:
            other_tracks = [track for track in all_tracks if track not in underplayed]
            random.shuffle(other_tracks)
            underplayed.extend(other_tracks[:limit - len(underplayed)])
        
        # Ensure variety by artist and genre
        selected_tracks = []
        used_artists = set()
        used_genres = set()
        
        # First pass: select tracks with unique artists/genres
        for track in underplayed:
            if len(selected_tracks) >= limit:
                break
            
            artist_key = track.artist or 'Unknown'
            genre_key = track.genre or 'Unknown'
            
            if artist_key not in used_artists or genre_key not in used_genres:
                selected_tracks.append(track)
                used_artists.add(artist_key)
                used_genres.add(genre_key)
        
        # Second pass: fill remaining slots with any underplayed tracks
        remaining_tracks = [t for t in underplayed if t not in selected_tracks]
        while len(selected_tracks) < limit and remaining_tracks:
            selected_tracks.append(remaining_tracks.pop(0))
        
        random.shuffle(selected_tracks)
        
        return Playlist(
            id="auto_discovery",
            name="Discovery Mix",
            track_ids=[track.id for track in selected_tracks],
            date_created=datetime.now(),
            is_smart=True,
            smart_criteria={'type': 'discovery', 'limit': limit}
        )
    
    async def generate_workout_playlist(self, limit: int = 40, 
                                      min_bpm: int = 120) -> Optional[Playlist]:
        """Generate a high-energy workout playlist based on BPM."""
        all_tracks = await self.tracks.get_tracks()
        
        # Filter tracks by BPM if available
        energetic_tracks = []
        for track in all_tracks:
            if track.bpm and track.bpm >= min_bpm:
                energetic_tracks.append(track)
            elif not track.bpm and track.genre:
                # Include tracks from energetic genres if BPM unknown
                energetic_genres = ['rock', 'electronic', 'dance', 'hip hop', 'pop']
                if any(genre.lower() in track.genre.lower() for genre in energetic_genres):
                    energetic_tracks.append(track)
        
        if not energetic_tracks:
            return None
        
        # Select and shuffle
        if len(energetic_tracks) > limit:
            selected_tracks = random.sample(energetic_tracks, limit)
        else:
            selected_tracks = energetic_tracks
        
        # Sort by BPM if available, then shuffle within BPM ranges
        tracks_with_bpm = [t for t in selected_tracks if t.bpm]
        tracks_without_bpm = [t for t in selected_tracks if not t.bpm]
        
        tracks_with_bpm.sort(key=lambda t: t.bpm, reverse=True)
        random.shuffle(tracks_without_bpm)
        
        final_tracks = tracks_with_bpm + tracks_without_bpm
        
        return Playlist(
            id="auto_workout",
            name="Workout Mix",
            track_ids=[track.id for track in final_tracks],
            date_created=datetime.now(),
            is_smart=True,
            smart_criteria={'type': 'workout', 'min_bpm': min_bpm, 'limit': limit}
        )
    
    async def _get_most_played_tracks(self, tracks: List[Track], 
                                    min_count: int, limit: int) -> List[Track]:
        """Get tracks with highest play counts."""
        played_tracks = [t for t in tracks if t.play_count >= min_count]
        played_tracks.sort(key=lambda t: t.play_count, reverse=True)
        return played_tracks[:limit]
    
    async def _get_recently_added_tracks(self, tracks: List[Track], 
                                       days: int, limit: int) -> List[Track]:
        """Get tracks added within the specified number of days."""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_tracks = [
            t for t in tracks 
            if t.date_added and t.date_added >= cutoff_date
        ]
        recent_tracks.sort(key=lambda t: t.date_added or datetime.min, reverse=True)
        return recent_tracks[:limit]
    
    async def _get_never_played_tracks(self, tracks: List[Track], limit: int) -> List[Track]:
        """Get tracks that have never been played."""
        never_played = [t for t in tracks if t.play_count == 0]
        random.shuffle(never_played)  # Mix up the order
        return never_played[:limit]
    
    async def _get_highly_rated_tracks(self, tracks: List[Track], 
                                     min_rating: int, limit: int) -> List[Track]:
        """Get tracks with high ratings."""
        rated_tracks = [t for t in tracks if t.rating >= min_rating]
        rated_tracks.sort(key=lambda t: (t.rating, t.play_count), reverse=True)
        return rated_tracks[:limit]
    
    async def _get_recently_played_tracks(self, tracks: List[Track], 
                                        days: int, limit: int) -> List[Track]:
        """Get tracks played recently."""
        # Note: This would require last_played field in Track model
        # For now, use tracks with high play count and recent modification
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_tracks = [
            t for t in tracks 
            if t.date_modified and t.date_modified >= cutoff_date and t.play_count > 0
        ]
        recent_tracks.sort(key=lambda t: (t.date_modified or datetime.min, t.play_count), reverse=True)
        return recent_tracks[:limit]
    
    def _safe_filename(self, name: str) -> str:
        """Convert name to safe filename."""
        import re
        # Replace unsafe characters with underscores
        safe_name = re.sub(r'[^\w\-_.]', '_', name)
        return safe_name.lower()


class PlaylistAnalyzer:
    """Analyze existing playlists to suggest improvements."""
    
    def __init__(self, track_repository: Repository):
        self.tracks = track_repository
    
    async def analyze_playlist_diversity(self, playlist: Playlist) -> Dict[str, Any]:
        """Analyze diversity of tracks in playlist."""
        track_ids = playlist.track_ids
        tracks = []
        
        # Get track objects
        for track_id in track_ids:
            track = await self.tracks.get_track(track_id)
            if track:
                tracks.append(track)
        
        if not tracks:
            return {'error': 'No tracks found in playlist'}
        
        # Analyze diversity
        artists = [t.artist for t in tracks if t.artist]
        genres = [t.genre for t in tracks if t.genre]
        albums = [t.album for t in tracks if t.album]
        years = [t.year for t in tracks if t.year]
        
        artist_counts = Counter(artists)
        genre_counts = Counter(genres)
        album_counts = Counter(albums)
        year_counts = Counter(years)
        
        analysis = {
            'total_tracks': len(tracks),
            'unique_artists': len(set(artists)),
            'unique_genres': len(set(genres)),
            'unique_albums': len(set(albums)),
            'unique_years': len(set(years)),
            'most_common_artist': artist_counts.most_common(1)[0] if artist_counts else None,
            'most_common_genre': genre_counts.most_common(1)[0] if genre_counts else None,
            'artist_distribution': dict(artist_counts.most_common(5)),
            'genre_distribution': dict(genre_counts.most_common(5)),
            'year_range': f"{min(years)}-{max(years)}" if years else None,
            'total_duration': sum(t.duration or 0 for t in tracks),
            'average_rating': sum(t.rating for t in tracks) / len(tracks) if tracks else 0,
        }
        
        # Diversity score (higher is more diverse)
        diversity_score = 0
        if tracks:
            artist_diversity = len(set(artists)) / len(tracks)
            genre_diversity = len(set(genres)) / len(tracks) if genres else 0
            diversity_score = (artist_diversity + genre_diversity) / 2
        
        analysis['diversity_score'] = diversity_score
        
        # Suggestions
        suggestions = []
        if diversity_score < 0.3:
            suggestions.append("Consider adding tracks from different artists and genres")
        if len(set(years)) < 3 and len(years) > 5:
            suggestions.append("Add tracks from different time periods for variety")
        if analysis['average_rating'] < 3:
            suggestions.append("Consider replacing lower-rated tracks")
        
        analysis['suggestions'] = suggestions
        
        return analysis
    
    async def suggest_similar_tracks(self, playlist: Playlist, limit: int = 10) -> List[Track]:
        """Suggest tracks similar to those in the playlist."""
        track_ids = set(playlist.track_ids)
        playlist_tracks = []
        
        # Get playlist track objects
        for track_id in track_ids:
            track = await self.tracks.get_track(track_id)
            if track:
                playlist_tracks.append(track)
        
        if not playlist_tracks:
            return []
        
        # Analyze playlist characteristics
        common_genres = Counter(t.genre for t in playlist_tracks if t.genre).most_common(3)
        common_artists = Counter(t.artist for t in playlist_tracks if t.artist).most_common(5)
        
        # Get all tracks not in playlist
        all_tracks = await self.tracks.get_tracks()
        candidate_tracks = [t for t in all_tracks if t.id not in track_ids]
        
        # Score tracks based on similarity
        scored_tracks = []
        for track in candidate_tracks:
            score = 0
            
            # Genre match
            if track.genre:
                for genre, count in common_genres:
                    if track.genre == genre:
                        score += count * 2
            
            # Artist match
            if track.artist:
                for artist, count in common_artists:
                    if track.artist == artist:
                        score += count * 3
            
            # Album artist match (for compilation albums)
            if track.albumartist:
                for artist, count in common_artists:
                    if track.albumartist == artist:
                        score += count * 1.5
            
            if score > 0:
                scored_tracks.append((track, score))
        
        # Sort by score and return top suggestions
        scored_tracks.sort(key=lambda x: x[1], reverse=True)
        return [track for track, score in scored_tracks[:limit]]


# Global instances for use across the application
def create_smart_playlist_generator(track_repository: Repository) -> SmartPlaylistGenerator:
    """Create a smart playlist generator with the given repository."""
    return SmartPlaylistGenerator(track_repository)

def create_playlist_analyzer(track_repository: Repository) -> PlaylistAnalyzer:
    """Create a playlist analyzer with the given repository."""
    return PlaylistAnalyzer(track_repository)