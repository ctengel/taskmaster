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
    cards: list["Card"] = Relationship(back_populates="list_")


class CardBase(SQLModel):
    """Base card from which all other cards are modeled"""
    card_name: str
    card_due: Optional[datetime.date] = None
    category_id: int = Field(foreign_key="category.category_id")
    list_order: Optional[int] = None
    card_open: Optional[datetime.date] = None
    card_closed: Optional[datetime.date] = None
    card_duplicate: bool = False
    card_pom_tgt: Optional[int] = None


class Card(CardBase, table=True):
    """An index card or task"""
    card_id: int = Field(primary_key = True)
    list_id: int = Field(foreign_key="list.list_id")
    list_: List = Relationship(back_populates="cards")

class CardWithoutList(CardBase):
    """A card explicitly without a list... to prevent infinite recursion"""
    card_id: int
    list_id: int

class CardMove(SQLModel):
    """A request to move a single card"""
    list_id: Optional[int] = None
    list_order: Optional[int] = None
    after_card: Optional[int] = None
    before_card: Optional[int] = None

class ListWithCards(ListBase):
    """A list that includes details of cards on it"""
    list_id: int
    cards: list[CardWithoutList] = []

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
    # NOTE This may be overly complicated
    assert not (before and after)
    existing_orders = sorted({x.list_order for x in existing if x.list_order is not None})
    if not existing_orders:
        # If no existing orders, just put it in the middle
        return int((MIN_ORDER + MAX_ORDER)/2)
    if not before and not after:
        # If no preference has been given, just put it at the end
        return int((max(existing_orders) + MAX_ORDER)/2)
    target_id = before if before else after
    target_cards = [x for x in existing if x.card_id == target_id]
    assert len(target_cards) == 1
    target_card = target_cards[0]
    target_order = target_card.list_order
    if target_order is None:
        # If the card we want to go before/after doesn't have an order,
        #   just put at beginning or end
        if before:
            return int((min(existing_orders) + MIN_ORDER)/2)
        return int((max(existing_orders) + MAX_ORDER)/2)
    # Finally, if we can find our rightful place, insert appropriately,
    #   careful to take into account we may be first or last
    target_place = existing_orders.index(target_order)
    if before:
        if target_place == 0:
            return int((MIN_ORDER + target_order)/2)
        return int((existing_orders[target_place-1] + target_order)/2)
    if target_place == len(existing_orders) - 1:
        return int((MAX_ORDER + target_order)/2)
    return int((existing_orders[target_place+1] + target_order)/2)

def card_list_order(card: Card) -> int:
    """Given a card, return the order; safe for sorting"""
    if not card.list_order:
        return 0
    return card.list_order


@app.get("/lists/{list_id}", response_model=ListWithCards)
def get_list(*, session: Session = Depends(get_session), list_id: int):
    """Get a list of cards by ID"""
    list_ = session.get(List, list_id)
    if not list_:
        raise HTTPException(status_code=404)
    # TODO is there a way to ask SQL to do this for us
    list_.cards.sort(key=card_list_order)
    return list_

@app.post("/lists/{list_id}/cards/", response_model=Card)
def post_card(*, session: Session = Depends(get_session), list_id: int, card: CardBase):
    """Add a card to a list"""
    list_ = session.get(List, list_id)
    if not list_:
        raise HTTPException(status_code=404)
    new_card = Card(list_id=list_id, **card.dict())
    if not new_card.list_order:
        new_card.list_order = generate_list_order(list_.cards)
    session.add(new_card)
    session.commit()
    session.refresh(new_card)
    return new_card

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
        if card_move.list_id:
            # NOTE this may be inefficient
            session.commit()
            session.refresh(card)
        all_cards = list(card.list_.cards)
        if card_move.before_card:
            card.list_order = generate_list_order(all_cards, before=card_move.before_card)
        elif card_move.after_card:
            card.list_order = generate_list_order(all_cards, after=card_move.after_card)
        else:
            card.list_order = generate_list_order(all_cards)
    session.commit()
    session.refresh(card)
    return card

@app.get("/lists/", response_model=list[List])
def get_lists(*, session: Session = Depends(get_session)):
    """Get all lists"""
    lists = session.exec(select(List)).all()
    return lists

@app.get("/categories/", response_model=list[Category])
def get_categories(*, session: Session = Depends(get_session)):
    """Get all categories"""
    categories = session.exec(select(Category)).all()
    return categories

# TODO card completion
# TODO card update
# TODO mass list update - split or move
