import aiomysql

async def run(db):
    async with db._pool.acquire() as conn: # pylint: disable=W0212
        conn: aiomysql.Connection
        async with conn.cursor() as cur:
            cur: aiomysql.Cursor
            # FOREIGN KEYS
            await cur.execute("ALTER TABLE FILE_LOCATION DROP FOREIGN KEY fk_file_ids_files")
            await cur.execute("ALTER TABLE USER_FILE DROP FOREIGN KEY fk_user_files_files")
            await cur.execute("ALTER TABLE FILE_GROUP_FILE DROP FOREIGN KEY fk_fg_user_file")

            # RENAME
            await cur.execute("ALTER TABLE TGFILE CHANGE COLUMN id media_id BIGINT UNSIGNED")
            await cur.execute("ALTER TABLE TGFILE CHANGE COLUMN is_deleted is_restricted BOOLEAN DEFAULT FALSE")
            await cur.execute("ALTER TABLE FILE_LOCATION CHANGE COLUMN id media_id BIGINT UNSIGNED")
            await cur.execute("ALTER TABLE USER_FILE CHANGE COLUMN id media_id BIGINT UNSIGNED")
            await cur.execute("ALTER TABLE FILE_GROUP_FILE CHANGE COLUMN id media_id BIGINT UNSIGNED")

            # TGUSER
            await cur.execute("""
                ALTER TABLE TGUSER
                MODIFY COLUMN preferred_lang VARCHAR(5) NOT NULL DEFAULT 'en'
            """)

            await cur.execute("""
                ALTER TABLE TGUSER
                ADD COLUMN metadata JSON NOT NULL DEFAULT (JSON_OBJECT())
            """)

            # metadata
            await cur.execute("""
                ALTER TABLE TGFILE
                ADD COLUMN metadata JSON NOT NULL DEFAULT (JSON_OBJECT())
            """)

            await cur.execute("""
                ALTER TABLE USER_FILE
                ADD COLUMN metadata JSON NOT NULL DEFAULT (JSON_OBJECT())
            """)

            await cur.execute("""
                ALTER TABLE FILE_GROUP_FILE
                ADD COLUMN metadata JSON NOT NULL DEFAULT (JSON_OBJECT())
            """)

            # FOREIGN KEYS
            await cur.execute("""
                ALTER TABLE FILE_LOCATION
                ADD CONSTRAINT fk_file_ids_files
                FOREIGN KEY (media_id)
                REFERENCES TGFILE(media_id)
                ON DELETE CASCADE
            """)

            await cur.execute("""
                ALTER TABLE USER_FILE
                ADD CONSTRAINT fk_user_files_files
                FOREIGN KEY (media_id)
                REFERENCES TGFILE(media_id)
                ON DELETE RESTRICT
            """)

            await cur.execute("""
                ALTER TABLE FILE_GROUP_FILE
                ADD CONSTRAINT fk_fg_user_file
                FOREIGN KEY (user_id, media_id)
                REFERENCES USER_FILE(user_id, media_id)
                ON DELETE CASCADE
            """)

        await conn.commit()
