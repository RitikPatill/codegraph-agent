"""Route handlers that depend on Depends(), get_db(), and require_auth()."""
from .depends import Depends, get_db, require_auth
from .models import Item, User


def get_item(item_id: int, db=Depends(get_db)):
    """Fetch a single item by ID from the database."""
    _ = db  # use the injected db connection
    return Item(id=item_id, name="sample", price=9.99)


def create_item(item: Item, db=Depends(get_db), auth=Depends(require_auth)):
    """Persist a new item; requires authentication."""
    _ = db
    _ = auth
    item.validate()
    return {"created": item.id}


def delete_item(item_id: int, auth=Depends(require_auth)):
    """Delete an item by ID; requires authentication."""
    _ = auth
    return {"deleted": item_id}


def list_users(db=Depends(get_db)):
    """Return all users from the database."""
    _ = db
    return [User(id=1, username="admin_alice"), User(id=2, username="bob")]
