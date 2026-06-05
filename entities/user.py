from flask_login import UserMixin
from dataclasses import dataclass
from typing import Optional

@dataclass(slots=True)
class User(UserMixin):
    id: int = 0
    username: Optional[str] = None
    password_hash: Optional[str] = None

    def save(self, conn):
        with conn, conn.cursor() as cur:
            cur.execute(
                    'INSERT INTO users (Username, PasswordHash) VALUES (%s,%s) RETURNING Id',
                    (self.username, self.password_hash))
            self.id = cur.fetchone()[0]
        
    @classmethod
    def get_by_id(cls, userid: int, conn) -> Optional["User"]:
        cur = conn.cursor()
        cur.execute('SELECT Id, Username, PasswordHash FROM users where Id = %s', (userid,))
        row = cur.fetchone()
        return cls(*row) if row else None
    
    @classmethod
    def get_by_username(cls, username: str, conn) -> Optional["User"]:
        cur = conn.cursor()
        cur.execute('SELECT Id, Username, PasswordHash FROM users WHERE Username = %s', (username,))
        row = cur.fetchone()
        return cls(*row) if row else None
