"""
Example command set template module.

To create new commands to populate the cmdset, see
examples/command.py.

To extend the character command set:
  - copy this file up one level to gamesrc/commands and name it
    something fitting.
  - change settings.CMDSET_CHARACTER to point to the new module's
    CharacterCmdSet class
  - import/add commands at the end of CharacterCmdSet's add() method.

To extend Player cmdset:
  - like character set, but point settings.PLAYER on your new cmdset.

To extend Unloggedin cmdset:
  - like default set, but point settings.CMDSET_UNLOGGEDIN on your new cmdset.

To add a wholly new command set:
  - copy this file up one level to gamesrc/commands and name it
    something fitting.
  - add a new cmdset class
  - add it to objects e.g. with obj.cmdset.add(path.to.the.module.and.class)

"""

from ev import CmdSet, Command
from ev import default_cmds

#from contrib import menusystem, lineeditor
#from contrib import misc_commands
#from contrib import chargen

from game.gamesrc.commands.use_command import CmdUse

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    This is an example of how to overload the default command
    set defined in src/commands/default/cmdset_character.py.

    Here we copy everything by calling the parent, but you can
    copy&paste any combination of the default command to customize
    your default set. Next you change settings.CMDSET_CHARACTER to point
    to this class.
    """
    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        # calling setup in src.commands.default.cmdset_character
        super(CharacterCmdSet, self).at_cmdset_creation()

        #
        # any commands you add below will overload the default ones.
        #
        #self.add(menusystem.CmdMenuTest())
        #self.add(lineeditor.CmdEditor())
        #self.add(misc_commands.CmdQuell())
        self.add(CmdUse())

