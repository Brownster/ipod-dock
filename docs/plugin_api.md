# Plugin API

This document describes the simple REST interface provided by the project. It is intended for developers writing integrations (for example MusicBee or AudioBookShelf plugins) that need to send audio files to the Raspberry Pi and manage the iPod library.

## Starting the server

Run the FastAPI application with:

```bash
python -m ipod_sync.app
```

By default it listens on port `8000` on all interfaces. The examples below assume the Pi is reachable as `http://<pi>:8000`.

All endpoints require an `X-API-Key` header matching the secret configured on the server. Set the `IPOD_API_KEY` environment variable to define the key.

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
curl -H "X-API-Key: <key>" -F "file=@song.mp3" http://<pi>:8000/upload
```

A successful request returns the queued filename:

```json
{"queued": "song.mp3"}
```

Files are written to the queue directory on the Pi and processed by the sync script.

### `POST /upload/{category}`
Upload a file to a specific category. `category` must be one of `music`, `audiobook` or `podcast`.

```bash
curl -H "X-API-Key: <key>" -F "file=@book.m4b" http://<pi>:8000/upload/audiobook
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

### `POST /podcasts/fetch`
Download episodes from an RSS feed and add them to the queue. The request body
must provide a JSON object containing `feed_url`.

```bash
curl -X POST -H "X-API-Key: <key>" -H "Content-Type: application/json" \
     -d '{"feed_url": "https://example.com/feed.rss"}' \
     http://<pi>:8000/podcasts/fetch
```

The response lists the filenames that were downloaded.

### `GET /stats`
Return basic dashboard information such as track count, queue size and storage usage.

### `GET /api/library`
List books in your Audible library. Requires `audible-cli` to be authenticated on the server.

### `POST /api/convert`
Queue a book for conversion. Provide a JSON object containing `asin` and `title`.

### `GET /api/status`
Retrieve the status of all queued Audible conversions.

### `GET /downloads/{file}`
Download a completed M4B file. Converted books are also placed in the queue for syncing.

## Notes

Provide the correct `X-API-Key` header with every request or the server will return `401 Unauthorized`. Uploaded files in formats the iPod does not natively support will be converted to MP3 using `ffmpeg` during the sync step.
