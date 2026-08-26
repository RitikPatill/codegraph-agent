"""Domain models for the sample web framework slice."""


class Item:
    def __init__(self, id: int, name: str, price: float) -> None:
        self.id = id
        self.name = name
        self.price = price

    def validate(self) -> bool:
        """Return True if the item data is valid."""
        if not self.name:
            raise ValueError("Item name must not be empty")
        if self.price < 0:
            raise ValueError("Item price must be non-negative")
        return True


class User:
    def __init__(self, id: int, username: str) -> None:
        self.id = id
        self.username = username

    def is_admin(self) -> bool:
        """Return True if this user has admin privileges."""
        return self.username.startswith("admin_")
