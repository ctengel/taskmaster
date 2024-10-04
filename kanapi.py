import datetime
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import Field, SQLModel, Session, create_engine

SQLITE_FILE = 'kanban.test.db'
SQLITE_URL = f"sqlite:///{SQLITE_FILE}"

class Category(SQLModel, table=True):
    category_id: int = Field(primary_key = True)
    category_name: str
    category_color: Optional[str] = None

class Board(SQLModel, table=True):
    board_id: int = Field(primary_key = True)
    user: Optional[str] = None
    category_id: Optional[int] = Field(default=None, foreign_key="category.category_id")

class List(SQLModel, table=True):
    list_id: int = Field(primary_key = True)
    list_name: str
    board_order: Optional[int] = None
    category_id: Optional[int] = Field(default=None, foreign_key="category.category_id")
    list_limit: Optional[int] = None
    list_wakeup: Optional[datetime.date] = None
    board_id: Optional[int] = Field(default=None, foreign_key="board.board_id")
    list_closed: bool = False
    board_summary: bool = False
    list_poms_disp: bool = False

class Card(SQLModel, table=True):
    card_id: int = Field(primary_key = True)
    card_name: str
    card_due: Optional[datetime.date] = None
    category_id: int = Field(foreign_key="app.category_id")
    list_id: int = Field(foreign_key="list.list_id")
    list_order: Optional[int] = None
    card_open: Optional[datetime.date] = None
    card_closed: Optional[datetime.date] = None
    card_duplicate: bool = False
    card_pom_tgt: Optional[int] = None

connect_args = {"check_same_thread": False}
engine = create_engine(SQLITE_URL, echo=True, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

app = FastAPI(
        title="TaskMaster KanBan API"
        )

def get_session():
    with Session(engine) as session:
        yield session


@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.get("/lists/{list_id}", response_model=List)
def get_list(*, session: Session = Depends(get_session), list_id: int):
    list_ = session.get(List, list_id)
    if not list_:
        raise HTTPException(status_code=404)
    return list_

@app.post("/lists/{list_id}/cards/", response_model=Card)
def get_card(*, session: Session = Depends(get_session), list_id: int, card: Card):
    if not session.get(List, list_id):
        raise HTTPException(status_code=404)
    card.list_id = list_id
    session.add(card)
    session.commit()
    session.refresh(card)
    return card
