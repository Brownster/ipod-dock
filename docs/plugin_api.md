# Plugin API

This document describes the simple REST interface provided by the project. It is intended for developers writing integrations (for example MusicBee or AudioBookShelf plugins) that need to send audio files to the Raspberry Pi and manage the iPod library.

## Starting the server

Run the FastAPI application with:

```bash
python -m ipod_sync.app
```

By default it listens on port `8000` on all interfaces. The examples below assume the Pi is reachable as `http://<pi>:8000`.

## Endpoints

### `GET /status`
Returns a basic health check.

```json
{"status": "ok"}
```

### `POST /upload`
Upload an audio file. The request must use `multipart/form-data` with a single field named `file`.

Example using `curl`:

```bash
curl -F "file=@song.mp3" http://<pi>:8000/upload
```

A successful request returns the queued filename:

```json
{"queued": "song.mp3"}
```

Files are written to the queue directory on the Pi and processed by the sync script.

### `POST /upload/{category}`
Upload a file to a specific category. `category` must be either `music` or `audiobook`.

```bash
curl -F "file=@book.m4b" http://<pi>:8000/upload/audiobook
```

The response includes the queued filename and the category:

```json
{"queued": "book.m4b", "category": "audiobook"}
```

### `GET /tracks`
Retrieve the list of tracks currently on the iPod. Each item contains minimal metadata:

```json
[
  {"id": "1", "title": "Track Title", "artist": "Artist", "album": "Album"}
]
```

### `DELETE /tracks/{id}`
Remove a track by its database identifier. On success the response is:

```json
{"deleted": "<id>"}
```

A `404` status is returned if the track does not exist.

### `GET /queue`
Return a list of files waiting in the sync queue.

### `POST /queue/clear`
Remove all files from the queue.

### `POST /sync`
Import queued files onto the iPod immediately.

### `GET /stats`
Return basic dashboard information such as track count, queue size and storage usage.

## Notes

Authentication has not yet been implemented, so the API should only be exposed on trusted networks. Uploaded files must be in a format supported by the iPod (typically MP3 or AAC); conversion is outside the scope of the API.
