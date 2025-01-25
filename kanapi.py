"""KanBan API and DataBase"""

import datetime
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import Field, SQLModel, Session, create_engine, Relationship, select

SQLITE_FILE = 'kanban.test.db'
SQLITE_URL = f"sqlite:///{SQLITE_FILE}"
MIN_ORDER = 1
MAX_ORDER = 2147483646

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

class CardMove(SQLModel):
    """A request to move a single card"""
    list_id: Optional[int] = None
    list_order: Optional[int] = None
    after_card: Optional[int] = None
    before_card: Optional[int] = None

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

def generate_list_order(existing: list[Card], before: int = None, after: int = None) -> int:
    """Propose a list_order for a new or existing card based on existing items in the list"""
    assert not (before and after)
    existing_orders = sorted({x.list_order for x in existing if x.list_order is not None})
    if not existing_orders:
        return int((MIN_ORDER + MAX_ORDER)/2)
    if not before and not after:
        return int((max(existing_orders) + MAX_ORDER)/2)
    target_id = before if before else after
    target_cards = [x for x in existing if x.card_id == target_id]
    assert len(target_cards) == 1
    target_card = target_cards[0]
    target_order = target_card.list_order
    if target_order is None:
        if before:
            return int((min(existing_orders) + MIN_ORDER)/2)
        return int((max(existing_orders) + MAX_ORDER)/2)
    target_place = existing_orders.index(target_order)
    if before:
        return int((existing_orders[target_place-1] + target_order))/2
    return int((existing_orders[target_place+1] + target_order))/2


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
    list_ = session.get(List, list_id)
    if not list_:
        raise HTTPException(status_code=404)
    card.list_id = list_id
    if not card.list_order:
        card.list_order = generate_list_order(list_.cards)
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

@app.post("/cards/{card_id}/move", response_model=Card)
def move_card(*, session: Session = Depends(get_session), card_id: int, card_move: CardMove):
    """Move a card, either within a list or to a different list"""
    card = session.get(Card, card_id)
    if card_move.list_id:
        # TODO validate category etc
        card.list_id = card_move.list_id
    if card_move.list_order:
        # TODO do this as validation
        assert not card_move.before_card
        assert not card_move.after_card
        card.list_order = card_move.list_order
    else:
        assert not (card_move.before_card and card_move.after_card)
        # TODO refresh (to get correct list) and use list_ relationship i.e. card.list_.cards
        statement = select(Card).where(Card.list_id == card.list_id)
        all_cards = list(session.exec(statement))
        #all_cards = card.list_.cards
        if card_move.before_card:
            card.list_order = generate_list_order(all_cards, before=card_move.before_card)
        elif card_move.after_card:
            card.list_order = generate_list_order(all_cards, after=card_move.after_card)
        else:
            card.list_order = generate_list_order(all_cards)
    session.commit()
    session.refresh(card)
    return card

# TODO card completion
# TODO card update
# TODO mass list update - split or move
