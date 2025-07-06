#!/usr/bin/env python3
"""
Comprehensive test script for iPod Python bindings.
Based on real testing with iPod Video and libgpod.
"""

import gpod
import sys
import os
import argparse
from pathlib import Path

def test_ipod_read(ipod_path: str) -> bool:
    """Test reading iPod contents."""
    print(f"=== Testing iPod Read ===")
    try:
        print(f"Attempting to read iPod database from: {ipod_path}")
        
        # Initialize the iPod database
        db = gpod.Database(ipod_path)
        print("✅ Successfully opened iPod database!")
        
        # Get basic info
        print(f"📊 Number of tracks: {len(db)}")
        print(f"📊 Number of playlists: {len(db.Playlists)}")
        
        # List first few tracks
        print("\n🎵 First few tracks:")
        for i, track in enumerate(db[:5]):  # Show first 5 tracks
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
        print("\n📋 Playlists:")
        for i, playlist in enumerate(db.Playlists):
            print(f"  {i+1}. {playlist.name} ({len(playlist)} tracks)")
            
        return True
        
    except Exception as e:
        print(f"❌ Error reading iPod: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_add_track(ipod_path: str, mp3_file: str) -> bool:
    """Test adding an MP3 file to iPod."""
    print(f"\n=== Testing Track Addition ===")
    try:
        # Check if the MP3 file exists
        if not os.path.exists(mp3_file):
            print(f"❌ MP3 file not found: {mp3_file}")
            return False
            
        print(f"🎵 Testing with MP3 file: {mp3_file}")
        print(f"📁 File size: {os.path.getsize(mp3_file)} bytes")
        
        # Open the iPod database
        db = gpod.Database(ipod_path)
        print("✅ Successfully opened iPod database!")
        
        initial_count = len(db)
        print(f"📊 Initial number of tracks: {initial_count}")
        
        # Create a new track from file
        print("🔄 Creating track from file...")
        track = gpod.Track(mp3_file)
        
        # Set some metadata
        track['title'] = 'Test Track (Python Bindings)'
        track['artist'] = 'Test Artist'
        track['album'] = 'Test Album'
        track['genre'] = 'Test'
        
        print("✅ Track created successfully!")
        print(f"🏷️  Track title: {track['title']}")
        
        # Add the track to the database FIRST
        print("🔄 Adding track to database...")
        db.add(track)
        
        # Now copy the file to the iPod
        print("🔄 Copying file to iPod...")
        track.copy_to_ipod()
        print(f"✅ File copied to: {track['ipod_path']}")
        
        # Add to the main playlist
        if len(db.Playlists) > 0:
            main_playlist = db.Playlists[0]
            main_playlist.add(track)
            print(f"✅ Added to playlist: {main_playlist.name}")
        
        # Close the database to save changes
        print("🔄 Saving changes...")
        db.close()
        
        # Reopen to verify
        db2 = gpod.Database(ipod_path)
        final_count = len(db2)
        print(f"📊 Final number of tracks: {final_count}")
        print(f"✅ Successfully added {final_count - initial_count} track(s)!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_track_attributes(ipod_path: str) -> bool:
    """Test reading various track attributes."""
    print(f"\n=== Testing Track Attributes ===")
    try:
        db = gpod.Database(ipod_path)
        
        if len(db) == 0:
            print("⚠️  No tracks found on iPod")
            return True
        
        # Get first track
        track = db[0]
        print("🔍 Examining first track attributes:")
        
        # Test common attributes
        attributes = [
            'title', 'artist', 'album', 'genre', 'tracklen', 'size', 
            'track_nr', 'playcount', 'rating', 'ipod_path', 'mediatype'
        ]
        
        for attr in attributes:
            try:
                value = track[attr]
                if isinstance(value, bytes):
                    value = value.decode('utf-8', errors='replace')
                print(f"  {attr}: {value}")
            except KeyError:
                print(f"  {attr}: <not available>")
            except Exception as e:
                print(f"  {attr}: <error: {e}>")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing attributes: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Test iPod Python bindings')
    parser.add_argument('--ipod-path', '-p', default='/home/marc/ipod-dock/mnt/ipod',
                        help='Path to mounted iPod')
    parser.add_argument('--test-file', '-f',
                        help='MP3 file to test adding (optional)')
    parser.add_argument('--read-only', '-r', action='store_true',
                        help='Only test reading, do not add tracks')
    
    args = parser.parse_args()
    
    print("🍎 iPod Python Bindings Test Suite")
    print("=" * 50)
    
    # Check if iPod path exists
    if not os.path.exists(args.ipod_path):
        print(f"❌ iPod path does not exist: {args.ipod_path}")
        print("Make sure the iPod is mounted correctly.")
        return 1
    
    # Check for iPod structure
    ipod_control = Path(args.ipod_path) / "iPod_Control"
    if not ipod_control.exists():
        print(f"❌ iPod_Control directory not found at {args.ipod_path}")
        print("This doesn't appear to be a mounted iPod.")
        return 1
    
    print(f"✅ Found iPod at: {args.ipod_path}")
    
    # Test reading
    if not test_ipod_read(args.ipod_path):
        return 1
    
    # Test track attributes
    if not test_track_attributes(args.ipod_path):
        return 1
    
    # Test adding (if not read-only and test file provided)
    if not args.read_only and args.test_file:
        if not test_add_track(args.ipod_path, args.test_file):
            return 1
    elif not args.read_only:
        print("\n⚠️  No test file specified. Use --test-file to test adding tracks.")
        print("   Example: --test-file /path/to/test.mp3")
    
    print("\n✅ All tests completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())