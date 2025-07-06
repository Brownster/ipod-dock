# Python libgpod Bindings Testing Guide

This document provides tests and examples for working with the iPod using Python's `gpod` (libgpod) bindings, based on real-world testing with an iPod Video.

## Prerequisites

- iPod mounted with proper permissions (see mounting section below)
- Python `gpod` module installed (`python3-gpod` or compiled from source)
- MP3 or other supported audio files for testing

## Mounting the iPod

For the Python bindings to work correctly, the iPod must be mounted with proper permissions:

```bash
# Mount with user permissions (replace /dev/sda2 with your iPod partition)
sudo mount -t vfat -o uid=1000,gid=1000,umask=0022,rw,nosuid,nodev,noatime /dev/sda2 /mount/point
```

## Basic Testing Scripts

### 1. Test Reading iPod Contents

```python
#!/usr/bin/env python3
import gpod
import sys

def test_ipod_read():
    try:
        # iPod mount point
        ipod_path = "/home/marc/ipod-dock/mnt/ipod"
        print(f"Reading iPod database from: {ipod_path}")
        
        # Initialize the iPod database
        db = gpod.Database(ipod_path)
        print("Successfully opened iPod database!")
        
        # Get basic info
        print(f"Number of tracks: {len(db)}")
        print(f"Number of playlists: {len(db.Playlists)}")
        
        # List first few tracks
        if len(db) > 0:
            print("\nFirst few tracks:")
            for i, track in enumerate(db[:3]):
                # Use dictionary-style access for track attributes
                title = track['title'] or b'Unknown Title'
                artist = track['artist'] or b'Unknown Artist'
                album = track['album'] or b'Unknown Album'
                
                # Handle bytes objects
                if isinstance(title, bytes):
                    title = title.decode('utf-8', errors='replace')
                if isinstance(artist, bytes):
                    artist = artist.decode('utf-8', errors='replace')
                if isinstance(album, bytes):
                    album = album.decode('utf-8', errors='replace')
                
                print(f"  {i+1}. {title} - {artist} ({album})")
                print(f"     Duration: {track['tracklen']}ms, Size: {track['size']} bytes")
                print(f"     File: {track['ipod_path']}")
        
        # List playlists
        print("\nPlaylists:")
        for i, playlist in enumerate(db.Playlists):
            print(f"  {i+1}. {playlist.name} ({len(playlist)} tracks)")
            
        return True
        
    except Exception as e:
        print(f"Error reading iPod: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ipod_read()
    sys.exit(0 if success else 1)
```

### 2. Test Adding MP3 Files

```python
#!/usr/bin/env python3
import gpod
import sys
import os

def test_add_track():
    try:
        ipod_path = "/home/marc/ipod-dock/mnt/ipod"
        mp3_file = "/path/to/your/test.mp3"  # Change this path
        
        # Check if the MP3 file exists
        if not os.path.exists(mp3_file):
            print(f"MP3 file not found: {mp3_file}")
            return False
            
        print(f"Testing with MP3 file: {mp3_file}")
        
        # Open the iPod database
        db = gpod.Database(ipod_path)
        print("Successfully opened iPod database!")
        
        initial_count = len(db)
        print(f"Initial number of tracks: {initial_count}")
        
        # Create a new track from file
        print("Creating track from file...")
        track = gpod.Track(mp3_file)
        
        # Set metadata
        track['title'] = 'Test Track'
        track['artist'] = 'Test Artist'
        track['album'] = 'Test Album'
        track['genre'] = 'Test Genre'
        
        print("Track created successfully!")
        print(f"Track title: {track['title']}")
        
        # IMPORTANT: Add track to database FIRST
        print("Adding track to database...")
        db.add(track)
        
        # Now copy the file to the iPod
        print("Copying file to iPod...")
        track.copy_to_ipod()
        print(f"File copied to: {track['ipod_path']}")
        
        # Add to the main playlist
        if len(db.Playlists) > 0:
            main_playlist = db.Playlists[0]
            main_playlist.add(track)
            print(f"Added to playlist: {main_playlist.name}")
        
        # Close the database to save changes
        print("Closing database...")
        db.close()
        
        # Reopen to verify
        db2 = gpod.Database(ipod_path)
        final_count = len(db2)
        print(f"Final number of tracks: {final_count}")
        print(f"Successfully added {final_count - initial_count} track(s)!")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_add_track()
    sys.exit(0 if success else 1)
```

## Key Learnings and Best Practices

### 1. Proper Track Attribute Access

Use dictionary-style access for gpod tracks:

```python
# Correct way
title = track['title']
artist = track['artist']
duration = track['tracklen']

# Handle bytes objects
if isinstance(title, bytes):
    title = title.decode('utf-8', errors='replace')
```

### 2. Correct Track Addition Workflow

The correct order for adding tracks is crucial:

```python
# 1. Create track from file
track = gpod.Track(mp3_file)

# 2. Set metadata
track['title'] = 'My Title'
track['artist'] = 'My Artist'

# 3. Add to database FIRST (this associates track with database)
db.add(track)

# 4. Copy file to iPod
track.copy_to_ipod()

# 5. Add to playlist
main_playlist.add(track)

# 6. Save changes
db.close()
```

### 3. Available Track Attributes

Common track attributes available via dictionary access:

- `title`, `artist`, `album`, `genre`
- `tracklen` (duration in milliseconds)
- `size` (file size in bytes)
- `track_nr` (track number)
- `playcount`, `rating`
- `ipod_path` (path on iPod)
- `mediatype` (audio, audiobook, podcast)

### 4. Database Management

- Use `db.close()` to save changes (not `db.save()`)
- Always add tracks to database before calling `copy_to_ipod()`
- Set `db = None` after closing to force reconnection

### 5. Error Handling

```python
try:
    db = gpod.Database(ipod_path)
    # ... operations
    db.close()
except Exception as e:
    logger.error(f"iPod operation failed: {e}")
    # Handle cleanup
```

## Testing Results

Based on testing with an iPod Video:

- ✅ Reading existing tracks and playlists works correctly
- ✅ Adding MP3 files successfully copies to iPod structure
- ✅ Metadata is properly handled with UTF-8 encoding
- ✅ Playlist management functions correctly
- ✅ Database persistence works with `close()` method

## Common Issues and Solutions

### Issue: "AttributeError: 'NoneType' object has no attribute 'decode'"
**Solution:** Add track to database before calling `copy_to_ipod()`

### Issue: "Track.copy_to_ipod() takes 1 positional argument but 2 were given"
**Solution:** Use `track.copy_to_ipod()` without arguments, not `track.copy_to_ipod(filename)`

### Issue: Database changes not persisting
**Solution:** Use `db.close()` instead of `db.save()`

### Issue: Permission denied errors
**Solution:** Mount iPod with proper uid/gid permissions

## Integration with Project

The patterns tested here are implemented in:

- `ipod_sync/repositories/ipod_repository.py` - Main iPod interface
- `ipod_sync/sync_from_queue.py` - File syncing logic
- `ipod_sync/udev_listener.py` - Mounting logic

## Testing Commands

Run the built-in test script:

```bash
./test_bindings.sh
```

Or create your own test with the patterns above.