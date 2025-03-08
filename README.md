# Convert Sony Music Center Playlists

Tool for migrating playlists for Sony Music Center between devices

Inspired by https://xdaforums.com/t/export-playlists-from-sony-music-app.4495475/

From old device copy MusicCenter/metadata.db to db/old/metadata.db
Create a test playlist on new device.
From new device copy MusicCenter/metadata.db to db/new/metadata.db

## Setup

This uses `uv` : 
- uv sync

Running:
```
uv run run playlist_migrate.py
```
