from dataclasses import dataclass
import logging
import sqlite3
from typing import List


@dataclass
class Playlist:
    id: int | None
    type_: int  # 1 = User? 2 = Automatic?
    name: str
    date_added: int  # millisec since epoch: int(time.time() * 1000)
    date_modified: int  # millisec since epoch
    storage_uuid: str
    playlist_order: int | None  # Mostly Null.
    relative_path: str | None


@dataclass
class PlaylistMember:
    id: int | None
    playlist_id: int  # FK Playlist
    play_order: int
    storage_uuid: str  #
    relative_path: str


@dataclass
class Storage:
    id: int | None
    storage_uuid: str  #
    system_storage_uuid: str | None
    volume_id: int | None
    app_local_storage_id: str | None


@dataclass
class Track:
    storage_uuid: str  # Not null
    relative_path: str  # Not null
    date_added: int | None
    date_last_played: int | None


def find_playlist_by_name(
    con: sqlite3.Connection, playlist_name: str
) -> Playlist | None:
    cur = con.cursor()
    fields = [
        "_id",
        "type",
        "date_added",
        "date_modified",
        "storage_uuid",
        "playlist_order",
        "relative_path",
    ]
    for row in cur.execute(
        f"SELECT {','.join(fields)} FROM playlists WHERE name = ?", [playlist_name]
    ):
        [
            playlist_id,
            type_,
            date_added,
            date_modified,
            storage_uuid,
            playlist_order,
            relative_path,
        ] = row

        return Playlist(
            id=playlist_id,
            type_=type_,
            name=playlist_name,
            date_added=date_added,
            date_modified=date_modified,
            storage_uuid=storage_uuid,
            playlist_order=playlist_order,
            relative_path=relative_path,
        )

    return None


def get_playlist_members(
    con: sqlite3.Connection, playlist_id: int
) -> List[PlaylistMember]:
    cur = con.cursor()
    fields = [
        "_id",
        "playlist_id",
        "play_order",
        "storage_uuid",
        "relative_path",
    ]
    res = cur.execute(
        f"SELECT {','.join(fields)} FROM playlist_members WHERE playlist_id = ?",
        [playlist_id],
    )

    ret: List[PlaylistMember] = []
    for row in res:
        [id, playlist_id, play_order, storage_uuid, relative_path] = row
        ret.append(
            PlaylistMember(
                id=id,
                playlist_id=playlist_id,
                play_order=play_order,
                storage_uuid=storage_uuid,
                relative_path=relative_path,
            )
        )

    return ret


def delete_playlist_by_id(con: sqlite3.Connection, id: int) -> None:
    cur = con.cursor()
    logging.debug(f"Deleting playlist with {id=}")
    cur.execute("DELETE FROM playlist_members WHERE playlist_id = ?", [id])
    cur.execute("DELETE FROM playlists WHERE _id = ?", [id])


def insert_playlist(con: sqlite3.Connection, playlist: Playlist) -> int:
    cur = con.cursor()
    logging.debug(f"Insert playlist with name={playlist.name}")
    fields = [
        ("type", playlist.type_),
        ("name", playlist.name),
        ("date_added", playlist.date_added),
        ("date_modified", playlist.date_modified),
        ("storage_uuid", playlist.storage_uuid),
        ("playlist_order", playlist.playlist_order),
        ("relative_path", playlist.relative_path),
    ]
    cur.execute(
        f"INSERT INTO playlists ({",".join([f[0] for f in fields])}) VALUES({','.join(['?']*len(fields))})  RETURNING _id",
        [f[1] for f in fields],
    )
    id = cur.lastrowid
    playlist.id = id
    return id


def get_storages(con: sqlite3.Connection) -> List[Storage]:
    cur = con.cursor()
    fields = [
        "_id",
        "storage_uuid",
        "system_storage_uuid",
        "volume_id",
        "app_local_storage_id",
    ]
    res = cur.execute(f"SELECT {','.join(fields)} FROM storages")
    ret: List[Storage] = []
    for row in res:
        [id, storage_uuid, system_storage_uuid, volume_id, app_local_storage_id] = row
        ret.append(
            Storage(
                id=id,
                storage_uuid=storage_uuid,
                system_storage_uuid=system_storage_uuid,
                volume_id=volume_id,
                app_local_storage_id=app_local_storage_id,
            )
        )

    return ret


def find_storage_uuid(con: sqlite3.Connection):
    # Just take the first one. This may not be the right one!
    return get_storages(con)[0].storage_uuid


def insert_playlist_member(con: sqlite3.Connection, member: PlaylistMember) -> int:
    logging.debug(f'Insert {member.relative_path.split('/')[-1]}')
    cur = con.cursor()
    fields = [
        ("playlist_id", member.playlist_id),
        ("play_order", member.play_order),
        ("storage_uuid", member.storage_uuid),
        ("relative_path", member.relative_path),
    ]
    cur.execute(
        f"INSERT INTO playlist_members ({",".join([f[0] for f in fields])}) VALUES({','.join(['?']*len(fields))}) RETURNING _id",
        [f[1] for f in fields],
    )
    return cur.lastrowid


def migrate(old_db: str, new_db: str, playlist_name: str) -> None:
    con_old = sqlite3.connect(old_db)
    old_playlist = find_playlist_by_name(con_old, playlist_name)

    if old_playlist is None:
        raise RuntimeError("Playlist not found:", playlist_name)

    con_new = sqlite3.connect(new_db)
    new_playlist = find_playlist_by_name(con_new, playlist_name)

    if new_playlist:
        delete_playlist_by_id(con_new, new_playlist.id)

    new_playlist = Playlist(
        id=None,
        type_=old_playlist.type_,
        name=playlist_name,
        date_added=old_playlist.date_added,
        date_modified=old_playlist.date_modified,
        storage_uuid=old_playlist.storage_uuid,
        playlist_order=old_playlist.playlist_order,
        relative_path=old_playlist.relative_path,
    )

    insert_playlist(con_new, new_playlist)

    storage_uuid = find_storage_uuid(con_new)

    old_members = get_playlist_members(con_old, old_playlist.id)
    for old_pl_member in old_members:
        relative_path = old_pl_member.relative_path
        # Perform any path modification here.
        # if relative_path:
        #    relative_path = "new/path/" + relative_path

        new_pl_member = PlaylistMember(
            id=None,
            playlist_id=new_playlist.id,
            play_order=old_pl_member.play_order,
            storage_uuid=storage_uuid,
            relative_path=relative_path,
        )

        insert_playlist_member(con_new, new_pl_member)
    con_new.commit()


def main():
    logging.basicConfig(level=logging.DEBUG)
    migrate("db/old/metadata.db", "db/new/metadata.db", playlist_name="trancey")


if __name__ == "__main__":
    main()
