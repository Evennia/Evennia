"""
This module gathers all the essential database-creation
functions for the game engine's various object types.

Only objects created 'stand-alone' are in here, e.g. object Attributes
are always created directly through their respective objects.

Each creation_* function also has an alias named for the entity being
created, such as create_object() and object().  This is for
consistency with the utils.search module and allows you to do the
shorter "create.object()".

The respective object managers hold more methods for manipulating and
searching objects already existing in the database.

Models covered:
 Objects
 Scripts
 Help
 Message
 Channel
 Players
"""
from django.conf import settings
from django.db import IntegrityError
from django.utils import timezone
from evennia.utils import logger
from evennia.utils.utils import make_iter, class_from_module, dbid_to_obj

# delayed imports
_User = None
_ObjectDB = None
_Object = None
_Script = None
_ScriptDB = None
_HelpEntry = None
_Msg = None
_Player = None
_PlayerDB = None
_to_object = None
_ChannelDB = None
_channelhandler = None


# limit symbol import from API
__all__ = ("create_object", "create_script", "create_help_entry",
           "create_message", "create_channel", "create_player")

_GA = object.__getattribute__

#
# Game Object creation
#

def create_object(typeclass=None, key=None, location=None,
                  home=None, permissions=None, locks=None,
                  aliases=None, destination=None, report_to=None, nohome=False):
    """

    Create a new in-game object.

    keywords:
        typeclass - class or python path to a typeclass
        key - name of the new object. If not set, a name of #dbref will be set.
        home - obj or #dbref to use as the object's home location
        permissions - a comma-separated string of permissions
        locks - one or more lockstrings, separated by semicolons
        aliases - a list of alternative keys
        destination - obj or #dbref to use as an Exit's target

        nohome - this allows the creation of objects without a default home location;
                 only used when creating the default location itself or during unittests
    """
    global _ObjectDB
    if not _ObjectDB:
        from evennia.objects.models import ObjectDB as _ObjectDB


    typeclass = typeclass if typeclass else settings.BASE_OBJECT_TYPECLASS

    if isinstance(typeclass, basestring):
        # a path is given. Load the actual typeclass
        typeclass = class_from_module(typeclass, settings.TYPECLASS_PATHS)

    # Setup input for the create command. We use ObjectDB as baseclass here
    # to give us maximum freedom (the typeclasses will load
    # correctly when each object is recovered).

    location = dbid_to_obj(location, _ObjectDB)
    destination = dbid_to_obj(destination, _ObjectDB)
    home = dbid_to_obj(home, _ObjectDB)
    if not home:
        try:
            home = dbid_to_obj(settings.DEFAULT_HOME, _ObjectDB) if not nohome else None
        except _ObjectDB.DoesNotExist:
            raise _ObjectDB.DoesNotExist("settings.DEFAULT_HOME (= '%s') does not exist, or the setting is malformed." %
                                         settings.DEFAULT_HOME)

    # create new instance
    new_object = typeclass(db_key=key, db_location=location,
                              db_destination=destination, db_home=home,
                              db_typeclass_path=typeclass.path)
    # store the call signature for the signal
    new_object._createdict = {"key":key, "location":location, "destination":destination,
                              "home":home, "typeclass":typeclass.path, "permissions":permissions,
                              "locks":locks, "aliases":aliases, "destination":destination,
                              "report_to":report_to, "nohome":nohome}
    # this will trigger the save signal which in turn calls the
    # at_first_save hook on the typeclass, where the _createdict can be
    # used.
    new_object.save()
    return new_object

#alias for create_object
object = create_object


#
# Script creation
#

def create_script(typeclass, key=None, obj=None, player=None, locks=None,
                  interval=None, start_delay=None, repeats=None,
                  persistent=None, autostart=True, report_to=None):
    """
    Create a new script. All scripts are a combination
    of a database object that communicates with the
    database, and an typeclass that 'decorates' the
    database object into being different types of scripts.
    It's behaviour is similar to the game objects except
    scripts has a time component and are more limited in
    scope.

    Argument 'typeclass' can be either an actual
    typeclass object or a python path to such an object.
    Only set key here if you want a unique name for this
    particular script (set it in config to give
    same key to all scripts of the same type). Set obj
    to tie this script to a particular object.

    See evennia.scripts.manager for methods to manipulate existing
    scripts in the database.

    report_to is an obtional object to receive error messages.
              If report_to is not set, an Exception with the
              error will be raised. If set, this method will
              return None upon errors.
    """
    global _ScriptDB
    if not _ScriptDB:
        from evennia.scripts.models import ScriptDB as _ScriptDB

    typeclass = typeclass if typeclass else settings.BASE_SCRIPT_TYPECLASS

    if isinstance(typeclass, basestring):
        # a path is given. Load the actual typeclass
        typeclass = class_from_module(typeclass, settings.TYPECLASS_PATHS)

    # validate input
    kwarg = {}
    if key: kwarg["db_key"] = key
    if player: kwarg["db_player"] = dbid_to_obj(player, _ScriptDB)
    if obj: kwarg["db_obj"] = dbid_to_obj(obj, _ScriptDB)
    if interval: kwarg["db_interval"] = interval
    if start_delay: kwarg["db_start_delay"] = start_delay
    if repeats: kwarg["db_repeats"] = repeats
    if persistent: kwarg["db_persistent"] = persistent

    # create new instance
    new_script = typeclass(**kwarg)

    # store the call signature for the signal
    new_script._createdict = {"key":key, "obj":obj, "player":player,
                              "locks":locks, "interval":interval,
                              "start_delay":start_delay, "repeats":repeats,
                              "persistent":persistent, "autostart":autostart,
                              "report_to":report_to}

    # this will trigger the save signal which in turn calls the
    # at_first_save hook on the tyepclass, where the _createdict
    # can be used.
    new_script.save()
    return new_script

#alias
script = create_script


#
# Help entry creation
#

def create_help_entry(key, entrytext, category="General", locks=None):
    """
    Create a static help entry in the help database. Note that Command
    help entries are dynamic and directly taken from the __doc__ entries
    of the command. The database-stored help entries are intended for more
    general help on the game, more extensive info, in-game setting information
    and so on.
    """
    global _HelpEntry
    if not _HelpEntry:
        from evennia.help.models import HelpEntry as _HelpEntry

    try:
        new_help = _HelpEntry()
        new_help.key = key
        new_help.entrytext = entrytext
        new_help.help_category = category
        if locks:
            new_help.locks.add(locks)
        new_help.save()
        return new_help
    except IntegrityError:
        string = "Could not add help entry: key '%s' already exists." % key
        logger.log_errmsg(string)
        return None
    except Exception:
        logger.log_trace()
        return None
# alias
help_entry = create_help_entry


#
# Comm system methods
#

def create_message(senderobj, message, channels=None,
                   receivers=None, locks=None, header=None):
    """
    Create a new communication message. Msgs are used for all
    player-to-player communication, both between individual players
    and over channels.
    senderobj - the player sending the message. This must be the actual object.
    message - text with the message. Eventual headers, titles etc
              should all be included in this text string. Formatting
              will be retained.
    channels - a channel or a list of channels to send to. The channels
             may be actual channel objects or their unique key strings.
    receivers - a player to send to, or a list of them. May be Player objects
               or playernames.
    locks - lock definition string
    header - mime-type or other optional information for the message

    The Comm system is created very open-ended, so it's fully possible
    to let a message both go to several channels and to several receivers
    at the same time, it's up to the command definitions to limit this as
    desired.
    """
    global _Msg
    if not _Msg:
        from evennia.comms.models import Msg as _Msg
    if not message:
        # we don't allow empty messages.
        return
    new_message = _Msg(db_message=message)
    new_message.save()
    for sender in make_iter(senderobj):
        new_message.senders = sender
    new_message.header = header
    for channel in make_iter(channels):
        new_message.channels = channel
    for receiver in make_iter(receivers):
        new_message.receivers = receiver
    if locks:
        new_message.locks.add(locks)
    new_message.save()
    return new_message
message = create_message


def create_channel(key, aliases=None, desc=None,
                   locks=None, keep_log=True,
                   typeclass=None):
    """
    Create A communication Channel. A Channel serves as a central
    hub for distributing Msgs to groups of people without
    specifying the receivers explicitly. Instead players may
    'connect' to the channel and follow the flow of messages. By
    default the channel allows access to all old messages, but
    this can be turned off with the keep_log switch.

    key - this must be unique.
    aliases - list of alternative (likely shorter) keynames.
    locks - lock string definitions
    """
    typeclass = typeclass if typeclass else settings.BASE_CHANNEL_TYPECLASS

    if isinstance(typeclass, basestring):
        # a path is given. Load the actual typeclass
        typeclass = class_from_module(typeclass, settings.TYPECLASS_PATHS)

    # create new instance
    new_channel = typeclass(db_key=key)

    # store call signature for the signal
    new_channel._createdict = {"key":key, "aliases":aliases,
            "desc":desc, "locks":locks, "keep_log":keep_log}

    # this will trigger the save signal which in turn calls the
    # at_first_save hook on the typeclass, where the _createdict can be
    # used.
    new_channel.save()
    return new_channel

channel = create_channel



#
# Player creation methods
#

def create_player(key, email, password,
                  typeclass=None,
                  is_superuser=False,
                  locks=None, permissions=None,
                  report_to=None):

    """
    This creates a new player.

    key - the player's name. This should be unique.
    email - email on valid addr@addr.domain form.
    password - password in cleartext
    is_superuser - wether or not this player is to be a superuser
    locks - lockstring
    permission - list of permissions
    report_to - an object with a msg() method to report errors to. If
                not given, errors will be logged.

    Will return the Player-typeclass or None/raise Exception if the
    Typeclass given failed to load.

    Concerning is_superuser:
     Usually only the server admin should need to be superuser, all
     other access levels can be handled with more fine-grained
     permissions or groups. A superuser bypasses all lock checking
     operations and is thus not suitable for play-testing the game.

    """
    global _PlayerDB
    if not _PlayerDB:
        from evennia.players.models import PlayerDB as _PlayerDB

    typeclass = typeclass if typeclass else settings.BASE_PLAYER_TYPECLASS

    if isinstance(typeclass, basestring):
        # a path is given. Load the actual typeclass.
        typeclass = class_from_module(typeclass, settings.TYPECLASS_PATHS)

    # setup input for the create command. We use PlayerDB as baseclass
    # here to give us maximum freedom (the typeclasses will load
    # correctly when each object is recovered).

    if not email:
        email = "dummy@dummy.com"
    if _PlayerDB.objects.filter(username__iexact=key):
        raise ValueError("A Player with the name '%s' already exists." % key)

    # this handles a given dbref-relocate to a player.
    report_to = dbid_to_obj(report_to, _PlayerDB)

    # create the correct player entity, using the setup from
    # base django auth.
    now = timezone.now()
    email = typeclass.objects.normalize_email(email)
    new_player = typeclass(username=key, email=email,
                           is_staff=is_superuser, is_superuser=is_superuser,
                           last_login=now, date_joined=now)
    new_player.set_password(password)
    new_player._createdict = {"locks":locks, "permissions":permissions,
                              "report_to":report_to}
    # saving will trigger the signal that calls the
    # at_first_save hook on the typeclass, where the _createdict
    # can be used.
    new_player.save()
    return new_player

# alias
player = create_player
