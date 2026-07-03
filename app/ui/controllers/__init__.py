"""Controllers wiring UI widgets to the services layer.

A controller is the only glue allowed between a "dumb" presentation widget and
business logic: it listens to the widget's intent signals, calls the
appropriate service, and pushes the result (or a friendly error) back into the
widget. No SQL or validation lives here.
"""

from app.ui.controllers.collection_controller import CollectionController

__all__ = ["CollectionController"]
