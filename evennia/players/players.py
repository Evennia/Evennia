"""
Typeclass for Player objects

Note that this object is primarily intended to
store OOC information, not game info! This
object represents the actual user (not their
character) and has NO actual precence in the
game world (this is handled by the associated
character object, so you should customize that
instead for most things).

"""

from django.conf import settings
from django.utils import timezone
from evennia.typeclasses.models import TypeclassBase
from evennia.players.manager import PlayerManager
from evennia.players.models import PlayerDB
from evennia.comms.models import ChannelDB
from evennia.commands import cmdhandler
from evennia.utils import logger
from evennia.utils.utils import (lazy_property, to_str,
                             make_iter, to_unicode,
                             variable_from_module)
from evennia.typeclasses.attributes import NickHandler
from evennia.scripts.scripthandler import ScriptHandler
from evennia.commands.cmdsethandler import CmdSetHandler

from django.utils.translation import ugettext as _

__all__ = ("DefaultPlayer",)

_SESSIONS = None

_AT_SEARCH_RESULT = variable_from_module(*settings.SEARCH_AT_RESULT.rsplit('.', 1))
_MULTISESSION_MODE = settings.MULTISESSION_MODE
_CMDSET_PLAYER = settings.CMDSET_PLAYER
_CONNECT_CHANNEL = None

class DefaultPlayer(PlayerDB):
    """
    This is the base Typeclass for all Players. Players represent
    the person playing the game and tracks account info, password
    etc. They are OOC entities without presence in-game. A Player
    can connect to a Character Object in order to "enter" the
    game.

    Player Typeclass API:

    * Available properties (only available on initiated typeclass objects)

     - key (string) - name of player
     - name (string)- wrapper for user.username
     - aliases (list of strings) - aliases to the object. Will be saved to
            database as AliasDB entries but returned as strings.
     - dbref (int, read-only) - unique #id-number. Also "id" can be used.
     - date_created (string) - time stamp of object creation
     - permissions (list of strings) - list of permission strings
     - user (User, read-only) - django User authorization object
     - obj (Object) - game object controlled by player. 'character' can also
                     be used.
     - sessions (list of Sessions) - sessions connected to this player
     - is_superuser (bool, read-only) - if the connected user is a superuser

    * Handlers

     - locks - lock-handler: use locks.add() to add new lock strings
     - db - attribute-handler: store/retrieve database attributes on this
                              self.db.myattr=val, val=self.db.myattr
     - ndb - non-persistent attribute handler: same as db but does not
                                  create a database entry when storing data
     - scripts - script-handler. Add new scripts to object with scripts.add()
     - cmdset - cmdset-handler. Use cmdset.add() to add new cmdsets to object
     - nicks - nick-handler. New nicks with nicks.add().

    * Helper methods

     - msg(outgoing_string, from_obj=None, **kwargs)
     - execute_cmd(raw_string)
     - search(ostring, global_search=False, attribute_name=None,
                      use_nicks=False, location=None,
                      ignore_errors=False, player=False)
     - is_typeclass(typeclass, exact=False)
     - swap_typeclass(new_typeclass, clean_attributes=False, no_default=True)
     - access(accessing_obj, access_type='read', default=False, no_superuser_bypass=False)
     - check_permstring(permstring)

    * Hook methods

     basetype_setup()
     at_player_creation()

     > note that the following hooks are also found on Objects and are
       usually handled on the character level:

     - at_init()
     - at_access()
     - at_cmdset_get(**kwargs)
     - at_first_login()
     - at_post_login(sessid=None)
     - at_disconnect()
     - at_message_receive()
     - at_message_send()
     - at_server_reload()
     - at_server_shutdown()

     """

    __metaclass__ = TypeclassBase

    objects = PlayerManager()

    # properties
    @lazy_property
    def cmdset(self):
        return CmdSetHandler(self, True)

    @lazy_property
    def scripts(self):
        return ScriptHandler(self)

    @lazy_property
    def nicks(self):
        return NickHandler(self)


    # session-related methods

    def get_session(self, sessid):
        """
        Retrieve given session.

        Args:
            sessid (int or list): A session id or list of such to retrieve.

        Returns:
            session (Session or list): One or more Sessions matching
                the given `sessid`s while also being connected to this
                Player.

        """
        global _SESSIONS
        if not _SESSIONS:
            from evennia.server.sessionhandler import SESSIONS as _SESSIONS
        return _SESSIONS.session_from_player(self, sessid)

    def get_all_sessions(self):
        """
        Get all sessions connected to this player.

        Returns:
            sessions (list): All Sessions currently connected to this
                player.

        """
        global _SESSIONS
        if not _SESSIONS:
            from evennia.server.sessionhandler import SESSIONS as _SESSIONS
        return _SESSIONS.sessions_from_player(self)
    sessions = property(get_all_sessions)  # alias shortcut

    def disconnect_session_from_player(self, sessid):
        """
        Access method for disconnecting a given session from the
        player (connection happens automatically in the
        sessionhandler)

        Args:
            sessid (int): Session id to disconnect.

        """
        # this should only be one value, loop just to make sure to
        # clean everything
        sessions = (session for session in self.get_all_sessions()
                    if session.sessid == sessid)
        for session in sessions:
            # this will also trigger unpuppeting
            session.sessionhandler.disconnect(session)

    # puppeting operations

    def puppet_object(self, sessid, obj):
        """
        Use the given session to control (puppet) the given object (usually
        a Character type).

        Args:
            sessid (int): session id of session to connect
            obj (Object): the object to start puppeting

        Raises:
            RuntimeError: If puppeting is not possible, the
                `exception.msg` will contain the reason.


        """
        # safety checks
        if not obj:
            raise RuntimeError("Object not found")
        session = self.get_session(sessid)
        if not session:
            raise RuntimeError("Session not found")
        if self.get_puppet(sessid) == obj:
            # already puppeting this object
            raise RuntimeError("You are already puppeting this object.")
        if not obj.access(self, 'puppet'):
            # no access
            raise RuntimeError("You don't have permission to puppet '%s'." % obj.key)
        if obj.player:
            # object already puppeted
            if obj.player == self:
                if obj.sessid.count():
                    # we may take over another of our sessions
                    # output messages to the affected sessions
                    if _MULTISESSION_MODE in (1, 3):
                        txt1 = "{c%s{n{G is now shared from another of your sessions.{n"
                        txt2 = "Sharing {c%s{n with another of your sessions."
                    else:
                        txt1 = "{c%s{n{R is now acted from another of your sessions.{n"
                        txt2 = "Taking over {c%s{n from another of your sessions."
                        self.unpuppet_object(obj.sessid.get())
                    self.msg(txt1 % obj.name, sessid=obj.sessid.get(), _forced_nomulti=True)
                    self.msg(txt2 % obj.name, sessid=sessid, _forced_nomulti=True)
            elif obj.player.is_connected:
                # controlled by another player
                raise RuntimeError("{R{c%s{R is already puppeted by another Player.")

        # do the puppeting
        if session.puppet:
            # cleanly unpuppet eventual previous object puppeted by this session
            self.unpuppet_object(sessid)
        # if we get to this point the character is ready to puppet or it
        # was left with a lingering player/sessid reference from an unclean
        # server kill or similar

        obj.at_pre_puppet(self, sessid=sessid)

        # do the connection
        obj.sessid.add(sessid)
        obj.player = self
        session.puid = obj.id
        session.puppet = obj
        # validate/start persistent scripts on object
        obj.scripts.validate()

        obj.at_post_puppet()

        # re-cache locks to make sure superuser bypass is updated
        obj.locks.cache_lock_bypass(obj)

    def unpuppet_object(self, sessid):
        """
        Disengage control over an object.

        Args:
            sessid(int): The session id to disengage.

        Raises:
            RuntimeError With message about error.

        """
        if _MULTISESSION_MODE == 1:
            sessions = self.get_all_sessions()
        else:
            sessions = self.get_session(sessid)
        if not sessions:
            raise RuntimeError("No session was found.")
        for session in make_iter(sessions):
            obj = session.puppet or None
            if not obj:
                raise RuntimeError("No puppet was found to disconnect from.")
            elif obj:
                # do the disconnect, but only if we are the last session to puppet
                obj.at_pre_unpuppet()
                obj.sessid.remove(session.sessid)
                if not obj.sessid.count():
                    del obj.player
                    obj.at_post_unpuppet(self, sessid=sessid)
            # Just to be sure we're always clear.
            session.puppet = None
            session.puid = None

    def unpuppet_all(self):
        """
        Disconnect all puppets. This is called by server before a
        reset/shutdown.
        """
        for session in (sess for sess in self.get_all_sessions() if sess.puppet):
            self.unpuppet_object(session.sessid)

    def get_puppet(self, sessid):
        """
        Get an object puppeted by this session through this player. This is
        the main method for retrieving the puppeted object from the
        player's end.

        Args:
            sessid (int): Find puppeted object based on this sessid.

        Returns:
            puppet (Object): The matching puppeted object, if any.

        """
        session = self.get_session(sessid)
        return session.puppet if session and session.puppet else None

    def get_all_puppets(self):
        """
        Get all currently puppeted objects.

        Returns:
            puppets (list): All puppeted objects currently controlled
                by this Player.

        """
        return list(set(session.puppet for session in self.get_all_sessions()
                                                    if session.puppet))

    def __get_single_puppet(self):
        """
        This is a legacy convenience link for use with `MULTISESSION_MODE`.

        Returns:
            puppets (Object or list): Users of `MULTISESSION_MODE` 0 or 1 will
                always get the first puppet back. Users of higher `MULTISESSION_MODE`s will
                get a list of all puppeted objects.

        """
        puppets = self.get_all_puppets()
        if _MULTISESSION_MODE in (0, 1):
            return puppets and puppets[0] or None
        return puppets
    character = property(__get_single_puppet)
    puppet = property(__get_single_puppet)

    # utility methods

    def delete(self, *args, **kwargs):
        """
        Deletes the player permanently.

        Notes:
            `*args` and `**kwargs` are passed on to the base delete
             mechanism (these are usually not used).

        """
        for session in self.get_all_sessions():
            # unpuppeting all objects and disconnecting the user, if any
            # sessions remain (should usually be handled from the
            # deleting command)
            try:
                self.unpuppet_object(session.sessid)
            except RuntimeError:
                # no puppet to disconnect from
                pass
            session.sessionhandler.disconnect(session, reason=_("Player being deleted."))
        self.scripts.stop()
        self.attributes.clear()
        self.nicks.clear()
        self.aliases.clear()
        super(PlayerDB, self).delete(*args, **kwargs)
    ## methods inherited from database model

    def msg(self, text=None, from_obj=None, sessid=None, **kwargs):
        """
        Evennia -> User
        This is the main route for sending data back to the user from the
        server.

        Args:
            text (str, optional): text data to send
            from_obj (Object or Player, optional): object sending. If given,
                its at_msg_send() hook will be called.
            sessid (int or list, optional): session id or ids to receive this
                send. If given, overrules MULTISESSION_MODE.
        Notes:
            All other keywords are passed on to the protocol.

        """
        text = to_str(text, force_string=True) if text else ""
        if from_obj:
            # call hook
            try:
                from_obj.at_msg_send(text=text, to_obj=self, **kwargs)
            except Exception:
                pass

        # session relay
        if sessid:
            # this could still be an iterable if sessid is an iterable
            sessions = self.get_session(sessid)
            if sessions:
                # this is a special instruction to ignore MULTISESSION_MODE
                # and only relay to this given session.
                kwargs["_nomulti"] = True
                for session in make_iter(sessions):
                    session.msg(text=text, **kwargs)
                return
        # we only send to the first of any connected sessions - the sessionhandler
        # will disperse this to the other sessions based on MULTISESSION_MODE.
        sessions = self.get_all_sessions()
        if sessions:
            sessions[0].msg(text=text, **kwargs)

    def execute_cmd(self, raw_string, sessid=None, **kwargs):
        """
        Do something as this player. This method is never called normally,
        but only when the player object itself is supposed to execute the
        command. It takes player nicks into account, but not nicks of
        eventual puppets.

        Args:
            raw_string (str): Raw command input coming from the command line.
            sessid (int, optional): The optional session id to be
                responsible for the command-send

        Kwargs:
            kwargs (any): Other keyword arguments will be added to the
                found command object instance as variables before it
                executes. This is unused by default Evennia but may be
                used to set flags and change operating paramaters for
                commands at run-time.

        """
        raw_string = to_unicode(raw_string)
        raw_string = self.nicks.nickreplace(raw_string,
                          categories=("inputline", "channel"), include_player=False)
        if not sessid and _MULTISESSION_MODE in (0, 1):
            # in this case, we should either have only one sessid, or the sessid
            # should not matter (since the return goes to all of them we can
            # just use the first one as the source)
            try:
                sessid = self.get_all_sessions()[0].sessid
            except IndexError:
                # this can happen for bots
                sessid = None
        return cmdhandler.cmdhandler(self, raw_string,
                                     callertype="player", sessid=sessid, **kwargs)

    def search(self, searchdata, return_puppet=False,
               nofound_string=None, multimatch_string=None, **kwargs):
        """
        This is similar to `DefaultObject.search` but will search for
        Players only.

        Args:
            searchdata (str or int): Search criterion, the Player's
                key or dbref to search for.
            return_puppet (bool, optional): Instructs the method to
                return matches as the object the Player controls rather
                than the Player itself (or None) if nothing is puppeted).
            nofound_string (str, optional): A one-time error message
                to echo if `searchdata` leads to no matches. If not given,
                will fall back to the default handler.
            multimatch_string (str, optional): A one-time error
                message to echo if `searchdata` leads to multiple matches.
                If not given, will fall back to the default handler.
        Notes:
            Extra keywords are ignored, but are allowed in call in
            order to make API more consistent with
            objects.models.TypedObject.search.

        """
        # handle me, self and *me, *self
        if isinstance(searchdata, basestring):
            # handle wrapping of common terms
            if searchdata.lower() in ("me", "*me", "self", "*self",):
                return self
        matches = self.__class__.objects.player_search(searchdata)
        matches = _AT_SEARCH_RESULT(self, searchdata, matches, global_search=True,
                                    nofound_string=nofound_string,
                                    multimatch_string=multimatch_string)
        if matches and return_puppet:
            try:
                return matches.puppet
            except AttributeError:
                return None
        return matches

    def access(self, accessing_obj, access_type='read', default=False, no_superuser_bypass=False, **kwargs):
        """
        Determines if another object has permission to access this
        object in whatever way.

        Args:
          accessing_obj (Object): Object trying to access this one.
          access_type (str, optional): Type of access sought.
          default (bool, optional): What to return if no lock of
            access_type was found
          no_superuser_bypass (bool, optional): Turn off superuser
            lock bypassing. Be careful with this one.

        Kwargs:
          kwargs (any): Passed to the at_access hook along with the result.

        Returns:
            result (bool): Result of access check.

        """
        result = super(DefaultPlayer, self).access(accessing_obj, access_type=access_type,
                                                   default=default, no_superuser_bypass=no_superuser_bypass)
        self.at_access(result, accessing_obj, access_type, **kwargs)
        return result

    ## player hooks

    def basetype_setup(self):
        """
        This sets up the basic properties for a player. Overload this
        with at_player_creation rather than changing this method.

        """
        # A basic security setup
        lockstring = "examine:perm(Wizards);edit:perm(Wizards);" \
                     "delete:perm(Wizards);boot:perm(Wizards);msg:all()"
        self.locks.add(lockstring)

        # The ooc player cmdset
        self.cmdset.add_default(_CMDSET_PLAYER, permanent=True)

    def at_player_creation(self):
        """
        This is called once, the very first time the player is created
        (i.e. first time they register with the game). It's a good
        place to store attributes all players should have, like
        configuration values etc.

        """
        # set an (empty) attribute holding the characters this player has
        lockstring = "attrread:perm(Admins);attredit:perm(Admins);" \
                     "attrcreate:perm(Admins)"
        self.attributes.add("_playable_characters", [], lockstring=lockstring)

    def at_init(self):
        """
        This is always called whenever this object is initiated --
        that is, whenever it its typeclass is cached from memory. This
        happens on-demand first time the object is used or activated
        in some way after being created but also after each server
        restart or reload. In the case of player objects, this usually
        happens the moment the player logs in or reconnects after a
        reload.

        """
        pass


    # Note that the hooks below also exist in the character object's
    # typeclass. You can often ignore these and rely on the character
    # ones instead, unless you are implementing a multi-character game
    # and have some things that should be done regardless of which
    # character is currently connected to this player.

    def at_first_save(self):
        """
        This is a generic hook called by Evennia when this object is
        saved to the database the very first time.  You generally
        don't override this method but the hooks called by it.

        """
        self.basetype_setup()
        self.at_player_creation()

        permissions = settings.PERMISSION_PLAYER_DEFAULT
        if hasattr(self, "_createdict"):
            # this will only be set if the utils.create_player
            # function was used to create the object.
            cdict = self._createdict
            if cdict.get("locks"):
                self.locks.add(cdict["locks"])
            if cdict.get("permissions"):
                permissions = cdict["permissions"]
            del self._createdict

        self.permissions.add(permissions)

    def at_access(self, result, accessing_obj, access_type, **kwargs):
        """
        This is triggered after an access-call on this Player has
            completed.

        Args:
            result (bool): The result of the access check.
            accessing_obj (any): The object requesting the access
                check.
            access_type (str): The type of access checked.

        Kwargs:
            kwargs (any): These are passed on from the access check
                and can be used to relay custom instructions from the
                check mechanism.

        Notes:
            This method cannot affect the result of the lock check and
            its return value is not used in any way. It can be used
            e.g.  to customize error messages in a central location or
            create other effects based on the access result.

        """
        pass

    def at_cmdset_get(self, **kwargs):
        """
        Called just *before* cmdsets on this player are requested by
        the command handler. The cmdsets are available as
        `self.cmdset`. If changes need to be done on the fly to the
        cmdset before passing them on to the cmdhandler, this is the
        place to do it.  This is called also if the player currently
        have no cmdsets. kwargs are usually not used unless the
        cmdset is generated dynamically.

        """
        pass

    def at_first_login(self):
        """
        Called the very first time this player logs into the game.

        """
        pass

    def at_pre_login(self):
        """
        Called every time the user logs in, just before the actual
        login-state is set.

        """
        pass

    def _send_to_connect_channel(self, message):
        """
        Helper method for loading and sending to the comm channel
        dedicated to connection messages.

        Args:
            message (str): A message to send to the connect channel.

        """
        global _CONNECT_CHANNEL
        if not _CONNECT_CHANNEL:
            try:
                _CONNECT_CHANNEL = ChannelDB.objects.filter(db_key=settings.DEFAULT_CHANNELS[1]["key"])[0]
            except Exception:
                logger.log_trace()
        now = timezone.now()
        now = "%02i-%02i-%02i(%02i:%02i)" % (now.year, now.month,
                                             now.day, now.hour, now.minute)
        if _CONNECT_CHANNEL:
            _CONNECT_CHANNEL.tempmsg("[%s, %s]: %s" % (_CONNECT_CHANNEL.key, now, message))
        else:
            logger.log_infomsg("[%s]: %s" % (now, message))

    def at_post_login(self, sessid=None):
        """
        Called at the end of the login process, just before letting
        the player loose.

        Args:
            sessid (int, optional): Session logging in, if any.

        Notes:
            This is called *before* an eventual Character's
            `at_post_login` hook. By default it is used to set up
            auto-puppeting based on `MULTISESSION_MODE`.

        """
        self._send_to_connect_channel("{G%s connected{n" % self.key)
        if _MULTISESSION_MODE == 0:
            # in this mode we should have only one character available. We
            # try to auto-connect to our last conneted object, if any
            self.puppet_object(sessid, self.db._last_puppet)
        elif _MULTISESSION_MODE == 1:
            # in this mode all sessions connect to the same puppet.
            self.puppet_object(sessid, self.db._last_puppet)
        elif _MULTISESSION_MODE in (2, 3):
            # In this mode we by default end up at a character selection
            # screen. We execute look on the player.
            self.execute_cmd("look", sessid=sessid)

    def at_failed_login(self, session):
        """
        Called by the login process if a user account is targeted correctly
        but provided with an invalid password. By default it does nothing,
        but exists to be overriden.

        Args:
            session (session): Session logging in.
        """
        pass

    def at_disconnect(self, reason=None):
        """
        Called just before user is disconnected.

        Args:
            reason (str, optional): The reason given for the disconnect,
                (echoed to the connection channel by default).

        """
        reason = reason and "(%s)" % reason or ""
        self._send_to_connect_channel("{R%s disconnected %s{n" % (self.key, reason))

    def at_post_disconnect(self):
        """
        This is called *after* disconnection is complete. No messages
        can be relayed to the player from here. After this call, the
        player should not be accessed any more, making this a good
        spot for deleting it (in the case of a guest player account,
        for example).
        """
        pass

    def at_message_receive(self, message, from_obj=None):
        """
        This is currently unused.

        """
        return True

    def at_message_send(self, message, to_object):
        """
        This is currently unused.

        """
        pass

    def at_server_reload(self):
        """
        This hook is called whenever the server is shutting down for
        restart/reboot. If you want to, for example, save
        non-persistent properties across a restart, this is the place
        to do it.
        """
        pass

    def at_server_shutdown(self):
        """
        This hook is called whenever the server is shutting down fully
        (i.e. not for a restart).
        """
        pass

    def add_new_character(self, character):
        """
        This method is called whenever a new character is added to a
        player's roster. Most useful in Multisession Mode 2+.
        """
        old_player = character.db._player
        if old_player:
            old_player.remove_character(character)
        character.locks.add("puppet:id(%i) or pid(%i) or perm(Immortals) or pperm(Immortals)" %
                                (character.id, self.id))
        self.db._playable_characters.append(character)

    def remove_character(self, character):
        """
        This method is called by add_new_character if a character
        already 'belongs' to a player. It cleans up the relevant
        data.
        """
        if character in self.db._playable_characters:
            self.db._playable_characters.remove(character)
        if self.db._last_puppet == character:
            del self.db._last_puppet

    @property
    def max_character_slots(self):
        """
        Returns an integer of how many characters a player can have.
        Checked by @charcreate. Just returns the value of
        MAX_NR_CHARACTERS by default. Useful for implementing
        flexible character slots.
        """
        return settings.MAX_NR_CHARACTERS

    @property
    def total_characters(self):
        """
        Returns an integer of how many character slots are in use.
        This calls the property .slot_exempt on each character, to
        account for special characters that might be exempt.
        """
        count = 0
        for character in self.db._playable_characters:
            if not character.slot_exempt:
                count += 1
        return count

    @property
    def total_characters_full(self):
        """
        Like total_characters, but ignores exempt status.
        """
        return len(self.db._playable_characters)

    def setup_starting_channels(self):
        """
        Called by utils.init_new_player() when a player is first created.
        Override to choose different starting channels.
        """
        # join the new player to the public channel
        pchannel = ChannelDB.objects.get_channel(settings.DEFAULT_CHANNELS[0]["key"])
        if not pchannel.connect(self):
            string = "New player '%s' could not connect to public channel!" % self.key
            logger.log_errmsg(string)


class DefaultGuest(DefaultPlayer):
    """
    This class is used for guest logins. Unlike Players, Guests and
    their characters are deleted after disconnection.
    """
    def at_post_login(self, sessid=None):
        """
        In theory, guests only have one character regardless of which
        MULTISESSION_MODE we're in. They don't get a choice.

        Args:
            sessid (int, optional): Id of Session connecting.

        """
        self._send_to_connect_channel("{G%s connected{n" % self.key)
        self.puppet_object(sessid, self.db._last_puppet)

    def at_disconnect(self):
        """
        A Guest's characters aren't meant to linger on the server.
        When a Guest disconnects, we remove its character.

        """
        super(DefaultGuest, self).at_disconnect()
        characters = self.db._playable_characters
        for character in filter(None, characters):
            character.delete()

    def at_server_shutdown(self):
        """
        We repeat the functionality of `at_disconnect()` here just to
        be on the safe side.
        """
        super(DefaultGuest, self).at_server_shutdown()
        characters = self.db._playable_characters
        for character in filter(None, characters):
            character.delete()

    def at_post_disconnect(self):
        """
        Guests aren't meant to linger on the server, either. We need
        to wait until after the Guest disconnects to delete it,
        though.
        """
        super(DefaultGuest, self).at_post_disconnect()
        self.delete()
