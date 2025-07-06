# libgpod Python Bindings API Documentation

This document provides comprehensive documentation for the libgpod Python bindings API based on hands-on experience with the iPod dock project.

## Overview

The libgpod library provides Python bindings for managing iPod databases. The main components are:
- `Database` - Represents the iPod's iTunes database
- `Track` - Represents individual audio files
- `Playlist` - Represents playlists containing tracks

## Database Class

### Constructor
```python
import gpod
db = gpod.Database(mountpoint)
```
- `mountpoint`: Path to the mounted iPod (e.g., `/mnt/ipod`)
- Raises `DatabaseException` if the database cannot be parsed

### Key Methods

#### Database Management
```python
db.close()                    # Close and save the database
db.copy_delayed_files()       # Copy pending files to iPod
db.smart_update()            # Update smart playlists
```

#### Track Management
```python
track = db.new_Track(filename='/path/to/file.mp3')  # Create new track from file
db.add(track)                                       # Add track to database
db.remove(track)                                    # Remove track from database
```

#### Playlist Management
```python
playlist = db.new_Playlist()     # Create new playlist
db.add(playlist)                 # Add playlist to database
db.remove(playlist)              # Remove playlist from database
```

#### Access Methods
```python
master = db.get_master()         # Get master playlist (contains all tracks)
playlists = db.get_playlists()   # Get all playlists
podcasts = db.get_podcasts()     # Get podcast playlist
```

### Available Attributes
- `Master` - Master playlist
- `Playlists` - List of all playlists
- `Podcasts` - Podcast playlist

## Track Class

### Constructor
```python
# Create from file
track = gpod.Track(filename='/path/to/file.mp3')

# Create empty track
track = gpod.Track()

# Create with specific media type
track = gpod.Track(filename='/path/to/file.mp3', mediatype=gpod.ITDB_MEDIATYPE_AUDIOBOOK)
```

### Key Methods
```python
track.copy_to_ipod()                              # Copy track file to iPod
track.set_coverart_from_file('/path/to/cover.jpg') # Set album artwork
track.set_podcast(True)                           # Mark as podcast
track.ipod_filename()                             # Get iPod file path
```

### Property Access
Tracks use dictionary-style access for properties:

```python
# Basic metadata
track['title']          # Song title (bytes, needs .decode('utf-8'))
track['artist']         # Artist name (bytes, needs .decode('utf-8'))
track['album']          # Album name (bytes, needs .decode('utf-8'))
track['genre']          # Genre (bytes, needs .decode('utf-8'))
track['composer']       # Composer (bytes, needs .decode('utf-8'))

# Technical info
track['dbid']           # Database ID (integer)
track['size']           # File size in bytes
track['tracklen']       # Track length in milliseconds
track['bitrate']        # Bitrate in kbps
track['samplerate']     # Sample rate in Hz
track['year']           # Release year

# Playback info
track['playcount']      # Play count
track['rating']         # Rating (0-100)
track['volume']         # Volume adjustment
track['time_added']     # Time added to library
track['time_played']    # Last played time

# Track numbers
track['track_nr']       # Track number
track['tracks']         # Total tracks on album
track['cd_nr']          # CD number
track['cds']           # Total CDs

# Flags
track['compilation']    # Compilation flag
track['checked']        # Checked for sync
track['visible']        # Visible in iPod interface
```

### String Encoding
**Important**: String properties are returned as bytes and need decoding:
```python
title = track['title'].decode('utf-8') if track['title'] else None
```

## Playlist Class

### Creating Playlists
```python
playlist = db.new_Playlist()
playlist.name = "My Playlist".encode('utf-8')  # Name must be encoded
```

### Methods
```python
playlist.add(track)        # Add track to playlist
playlist.remove(track)     # Remove track from playlist
playlist.randomize()       # Randomize track order
```

### Properties
```python
playlist.name             # Playlist name (bytes)
playlist.id               # Playlist ID
len(list(playlist))       # Number of tracks
```

### Iteration
```python
# Iterate through tracks in playlist
for track in playlist:
    print(track['title'])

# Convert to list
tracks = list(playlist)
```

## Common Patterns

### Adding a Track to iPod
```python
import gpod

# Open database
db = gpod.Database('/mnt/ipod')

try:
    # Create track from file
    track = db.new_Track(filename='/path/to/song.mp3')
    
    # Copy file to iPod
    track.copy_to_ipod()
    
    # Add to database
    db.add(track)
    
    # Save changes
    db.copy_delayed_files()
    
    print(f"Added track with ID: {track['dbid']}")
    
finally:
    db.close()
```

### Listing All Tracks
```python
import gpod

db = gpod.Database('/mnt/ipod')

try:
    master = db.get_master()
    tracks = []
    
    for track in list(master):
        tracks.append({
            'id': track['dbid'],
            'title': track['title'].decode('utf-8') if track['title'] else None,
            'artist': track['artist'].decode('utf-8') if track['artist'] else None,
            'album': track['album'].decode('utf-8') if track['album'] else None,
        })
    
    return tracks
    
finally:
    db.close()
```

### Creating a Playlist
```python
import gpod

db = gpod.Database('/mnt/ipod')

try:
    # Create playlist
    playlist = db.new_Playlist()
    playlist.name = "My Custom Playlist".encode('utf-8')
    
    # Add tracks by ID
    master = db.get_master()
    track_map = {str(t['dbid']): t for t in list(master)}
    
    for track_id in ['123', '456', '789']:  # Example track IDs
        if track_id in track_map:
            playlist.add(track_map[track_id])
    
    # Add to database
    db.add(playlist)
    db.copy_delayed_files()
    
finally:
    db.close()
```

### Deleting a Track
```python
import gpod

db = gpod.Database('/mnt/ipod')

try:
    master = db.get_master()
    
    # Find track by ID
    target_track = None
    for track in list(master):
        if str(track['dbid']) == str(track_id_to_delete):
            target_track = track
            break
    
    if target_track:
        db.remove(target_track)
        db.copy_delayed_files()
        print(f"Deleted track {track_id_to_delete}")
    else:
        print("Track not found")
        
finally:
    db.close()
```

## Media Types

Common media type constants:
```python
gpod.ITDB_MEDIATYPE_AUDIO      # Regular music
gpod.ITDB_MEDIATYPE_AUDIOBOOK  # Audiobooks
gpod.ITDB_MEDIATYPE_PODCAST    # Podcasts
gpod.ITDB_MEDIATYPE_MOVIE      # Video files
```

## Exception Handling

### Common Exceptions
- `gpod.DatabaseException` - Database parsing/saving errors
- `FileNotFoundError` - iPod not mounted or files missing
- `PermissionError` - Insufficient permissions

### Example Error Handling
```python
import gpod

try:
    db = gpod.Database('/mnt/ipod')
    # ... operations ...
    
except gpod.DatabaseException as e:
    print(f"Database error: {e}")
    # iPod might not be properly mounted or database corrupted
    
except FileNotFoundError as e:
    print(f"File not found: {e}")
    # iPod not mounted or file doesn't exist
    
except PermissionError as e:
    print(f"Permission denied: {e}")
    # Need proper mount permissions
    
finally:
    if 'db' in locals():
        db.close()
```

## Best Practices

1. **Always close the database**: Use try/finally or context managers
2. **Handle encoding**: Decode string properties from bytes to UTF-8
3. **Check permissions**: Ensure iPod is mounted with proper user permissions
4. **Error handling**: Wrap operations in try/catch blocks
5. **Save changes**: Call `copy_delayed_files()` after modifications
6. **File copying**: Call `copy_to_ipod()` after creating tracks from files

## Common Issues and Solutions

1. **"Unable to parse iTunes database"**
   - iPod not properly mounted
   - Database corruption
   - Insufficient permissions
   - **Solution**: Check mount status and permissions, remount iPod

2. **"object of type 'map' has no len()" (Python 2/3 Compatibility)**
   - This is a common issue when using Python 3 with libgpod
   - The `gpod.Track(filename)` constructor fails due to map() iterator vs list incompatibility
   - **Solution**: Use fallback track creation method (see project's `_create_gpod_track_from_file`)

3. **"'Track' object has no attribute 'get'"**
   - gpod Track objects don't support dictionary `.get()` method like regular Python dictionaries
   - **Solution**: Use try/except blocks with direct key access: `track['key']`

4. **String encoding errors**
   - gpod returns bytes objects that need decoding
   - **Solution**: Always decode bytes properties: `track['title'].decode('utf-8', errors='replace')`

5. **Permission denied on save**
   - Mount iPod with proper uid/gid options
   - Ensure service user owns the mount point
   - **Solution**: Mount with `-o uid=1000,gid=1000` options

6. **Database changes not persisting**
   - Not calling proper save method
   - **Solution**: Use `db.close()` instead of `db.save()` to persist changes

## Project Fixes for Python 2/3 Compatibility

This project includes several fixes for Python 2/3 compatibility issues with libgpod:

### IpodRepository Enhancements

1. **Robust Track Creation** (`_create_gpod_track_from_file`)
   - Handles `gpod.Track(filename)` constructor failures
   - Provides fallback to manual track creation
   - Includes automatic metadata extraction

2. **Fixed Track Conversion** (`_gpod_track_to_track`)
   - Replaces `.get()` method usage with try/except blocks
   - Proper handling of bytes string decoding
   - Safe access to all track properties

3. **Improved Add/Remove Methods**
   - `add_track()`: Uses robust track creation with fallback file copying
   - `remove_track()`: Properly finds tracks by iterating master playlist
   - Comprehensive validation and error handling

4. **Enhanced Error Handling**
   - Connection validation with mount point checks
   - File validation (size, format, existence)
   - Clear error messages for common issues

### Usage in Project

The fixed methods are available in `ipod_sync.repositories.ipod_repository.IpodRepository`:

```python
from ipod_sync.repositories.ipod_repository import IpodRepository
from ipod_sync.repositories import Track

# Create repository
repo = IpodRepository('/path/to/ipod')

# Add track (handles Python 2/3 compatibility automatically)
track = Track(
    title="My Song",
    artist="My Artist",
    file_path="/path/to/song.mp3",
    category="music"
)
track_id = repo.add_track(track)

# Remove track (properly finds track by ID)
success = repo.remove_track(track_id)

# Save changes
repo.save_changes()
```

## Version Notes

This documentation is based on the libgpod Python bindings as found in Debian Bookworm. API may vary between versions. Always test with your specific libgpod version.

**Python 2/3 Compatibility**: This project includes comprehensive fixes for Python 3 compatibility issues with libgpod, particularly around the `map()` iterator and `.get()` method problems.

## See Also

- [libgpod project](https://github.com/Brownster/libgpod)
- [gtkpod](http://www.gtkpod.org/) - GUI iPod manager using libgpod
- iPod database format documentation
- Project's `ipod_sync/repositories/ipod_repository.py` for implementation details
