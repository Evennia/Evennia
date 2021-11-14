"""
Components - ChrisLR 2021

This is a basic Component System.
It allows you to use components on typeclasses using a simple syntax.
This helps writing isolated code and reusing it over multiple objects.

## Installation

- To enable component support for a typeclass,
   import and inherit the ComponentHolderMixin, similar to this
  ```
  from evennia.contrib.components import ComponentHolderMixin
  class Character(ComponentHolderMixin, DefaultCharacter):
  ```

- Components need to inherit the Component class and must be registered to the listing
    Example:
    ```
    from evennia.contrib.components import Component, listing
    @listing.register
    class Health(Component):
        name = "health"
    ```

- Components may define DBFields at the class level
    Example:
    ```
    from evennia.contrib.components import Component, listing, DBField
    @listing.register
    class Health(Component):
        health = DBField(default_value=1)
    ```

    Note that default_value is optional and may be a callable such as `dict`

- Keep in mind that all components must be imported to be visible in the listing
  As such, I recommend regrouping them in a package
  You can then import all your components in that package's __init__

  Because of how Evennia import typeclasses and the behavior of python imports
  I recommend placing the components package inside the typeclasses.
"""


from . import listing
from .listing import register
from evennia.contrib.components.dbfield import DBField, NDBField
from evennia.contrib.components.component import Component
from evennia.contrib.components.holder import ComponentHolderMixin
