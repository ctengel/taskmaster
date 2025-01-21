"""KanBan API and DataBase"""

import datetime
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import Field, SQLModel, Session, create_engine, Relationship

SQLITE_FILE = 'kanban.test.db'
SQLITE_URL = f"sqlite:///{SQLITE_FILE}"

class Category(SQLModel, table=True):
    """A type of card with a given color, similar to a context"""
    category_id: int = Field(primary_key = True)
    category_name: str
    category_color: Optional[str] = None

class Board(SQLModel, table=True):
    """A KanBan board with lists on it"""
    board_id: int = Field(primary_key = True)
    user: Optional[str] = None
    category_id: Optional[int] = Field(default=None, foreign_key="category.category_id")

class ListBase(SQLModel):
    """A list of cards that may be on a Board"""
    list_name: str
    board_order: Optional[int] = None
    category_id: Optional[int] = Field(default=None, foreign_key="category.category_id")
    list_limit: Optional[int] = None
    list_wakeup: Optional[datetime.date] = None
    board_id: Optional[int] = Field(default=None, foreign_key="board.board_id")
    list_closed: bool = False
    board_summary: bool = False
    list_poms_disp: bool = False


class List(ListBase, table=True):
    """A table of lists"""
    list_id: int | None = Field(primary_key=True, default=None)
    cards: list["Card"] = Relationship()  # TODO back-populates


class Card(SQLModel, table=True):
    """An index card or task"""
    # TODO list relationship
    card_id: int = Field(primary_key = True)
    card_name: str
    card_due: Optional[datetime.date] = None
    category_id: int = Field(foreign_key="category.category_id")
    list_id: int = Field(foreign_key="list.list_id")
    list_order: Optional[int] = None
    card_open: Optional[datetime.date] = None
    card_closed: Optional[datetime.date] = None
    card_duplicate: bool = False
    card_pom_tgt: Optional[int] = None

class ListWithCards(ListBase):
    """A list that includes details of cards on it"""
    list_id: int
    cards: list[Card] = []

connect_args = {"check_same_thread": False}
engine = create_engine(SQLITE_URL, echo=True, connect_args=connect_args)

def create_db_and_tables():
    """Create DB schema"""
    SQLModel.metadata.create_all(engine)

app = FastAPI(
        title="TaskMaster KanBan API"
        )

def get_session():
    """Get a DB session"""
    with Session(engine) as session:
        yield session


@app.on_event("startup")
def on_startup():
    """Startup of app function that ensures schema creation"""
    create_db_and_tables()

@app.get("/lists/{list_id}", response_model=ListWithCards)
def get_list(*, session: Session = Depends(get_session), list_id: int):
    """Get a list of cards by ID"""
    # TODO order cards
    list_ = session.get(List, list_id)
    if not list_:
        raise HTTPException(status_code=404)
    return list_

@app.post("/lists/{list_id}/cards/", response_model=Card)
def post_card(*, session: Session = Depends(get_session), list_id: int, card: Card):
    """Add a card to a list"""
    if not session.get(List, list_id):
        raise HTTPException(status_code=404)
    card.list_id = list_id
    # TODO order list
    session.add(card)
    session.commit()
    session.refresh(card)
    return card

@app.post("/lists/", response_model=List)
def post_list(*, session: Session = Depends(get_session), list_: ListBase):
    """Create a list"""
    db_list = List.model_validate(list_)
    session.add(db_list)
    session.commit()
    session.refresh(db_list)
    return db_list

@app.post("/categories/", response_model=Category)
def post_category(*, session: Session = Depends(get_session), category_: Category):
    """Create a category"""
    session.add(category_)
    session.commit()
    session.refresh(category_)
    return category_
