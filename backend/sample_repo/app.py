"""Application factory for the sample web framework slice."""
from .depends import get_db
from .router import create_item, delete_item, get_item, list_users


class App:
    def __init__(self) -> None:
        self.routes: list = []
        self._started = False

    def include_router(self, router) -> None:
        """Register route handlers from *router*."""
        if isinstance(router, list):
            self.routes.extend(router)
        else:
            self.routes.append(router)

    def startup(self) -> None:
        """Run startup tasks (e.g. open DB pool)."""
        self._started = True
        _ = get_db()  # warm up the dependency


def create_app() -> App:
    """Instantiate, configure, and return the application."""
    application = App()
    application.include_router([get_item, create_item, delete_item, list_users])
    application.startup()
    return application
