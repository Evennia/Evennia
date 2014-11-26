import re
from .. command import MuxCommand
from .. lib.penn import header,table,msghead
from .. lib.EVDesc.models import Descfile

class CmdMultiDesc(MuxCommand):
    """
    +desc is a general multidescer, aka a bit of softcode used to save premade
    or existing @descs to your character for quick retrieval. This is useful
    for writing different appearances for different outfits or hairstyles, for
    example, and being able to switch with a simple command.

    +desc [<filename>]
    By itself, +desc lists all of your saved descriptions by name. Given a
    name, it switches you to that description. Your current @desc will be
    overwritten!

    +desc/noisy <filename>
    Works like +desc, but announces the change to the room. Useful for dramatics.

    +desc/save <filename>[=<description>]
    With only a filename entered, this command saves your current @desc to a
    desc file. If given a description after an equals sign, saves that to
    it instead.

    +desc/rename <filename>=<newname>
    Renames a description file.

    +desc/view <filename>
    Shows you one of your saved descs without changing to it.
    """
    
    key = "+desc"
    aliases = ("mdesc", "multidesc")
    locks = "cmd:all()"
    
    def func(self):
        "Here we go!"
        
        caller = self.caller
        switches = self.switches
        rhs = self.rhs
        lhs = self.lhs

        self.sysname = "INFO"
        self.isadmin = self.caller.locks.check_lockstring(self.caller, "dummy:perm(Wizards)")
        isadmin = self.isadmin
        playswitches = ['save','delete','view','rename']
        admswitches = []
        
        if isadmin:
            callswitches = playswitches + admswitches
        else:
            callswitches = playswitches
        switches = self.partial(switches,callswitches)

        if lhs:
            if not re.match('^\w+$',lhs):
                string = "Desc names must be addressed with alphanumeric words!"
                caller.msg(msghead(self.sysname,error=True) + string)
                return
            if len(lhs) > 18:
                string = "Desc names may not exceed 18 characters!"
                caller.msg(msghead(self.sysname,error=True) + string)
                return
            mdesc,created = Descfile.objects.get_or_create(cid=self.character.dbobj,title__iexact=lhs)
            
        if 'save' in switches:
            if not lhs:
                string = "Must include a desc name."
                caller.msg(msghead(self.sysname,error=True) + string)
                return
            if rhs:
                newdesc = rhs
            else:
                newdesc = caller.db.desc
            mdesc.title = lhs
            mdesc.text = newdesc
            mdesc.save()
            string = "Desc %s has been saved!" % lhs
            caller.msg(msghead(self.sysname) + string)
            return
        
        if 'delete' in switches:
            if not lhs:
                string = "Must include a desc name."
                caller.msg(msghead(self.sysname,error=True) + string)
                return
            if created:
                string = "Desc not found!"
                self.caller.msg(msghead(self.sysname,error=True) + string)
                return
            string = "Desc '%s' has been deleted!" % mdesc.title
            caller.msg(msghead(self.sysname,error=True) + string)
            mdesc.delete()
            return
        
        if 'view' in switches:
            if not lhs:
                string = "Must include a desc name."
                caller.msg(msghead(self.sysname,error=True) + string)
                return
            if not created:
                caller.msg(header("Desc Contents: %s" % mdesc.title) + "\n" + mdesc.text)
                caller.msg(header())
            else:
                string = "Desc '%s' not found." % lhs
                caller.msg(msghead(self.sysname,error=True) + string)
            return
        
        if 'rename' in switches:
            if not lhs:
                string = "Must include a desc name."
                caller.msg(msghead(self.sysname,error=True) + string)
                return
            if not created:
                if not rhs:
                    string = "Must include a new desc name."
                    caller.msg(msghead(self.sysname,error=True) + string)
                    return
                else:
                    mdesc2,created = Descfile.objects.get_or_create(cid=self.character.dbobj,title__iexact=rhs)
                    if created:
                        string = "Desc '%s' already exists." % mdesc2.title
                        caller.msg(msghead(self.sysname,error=True) + string)
                        return
                    else:
                        string = "Renaming Desc '%s' to '%s'" % (mdesc.title,rhs)
                        caller.msg(msghead(self.sysname) + string)
                        mdesc.title = rhs
                        mdesc.save()
                        return
            else:
                string = "Desc not found."
                caller.msg(msghead(self.sysname,error=True) + string)
                return
                
        if not switches or 'noisy' in switches:
            if not lhs:
                caller.msg(header("Your Saved Descs"))
                caller.msg(table(Descfile.objects.filter(cid=self.character.dbobj).values_list('title',flat=True),24,78))
                caller.msg(header())
                return
            if not created:
                caller.db.desc = mdesc.text
                caller.msg(msghead(self.sysname) + "Desc changed!")
                if 'noisy' in switches:
                    string = "%s changed their description to: %s" + (caller.key,mdesc.title)
                    caller.location.msg_contents(msghead(self.sysname) + string)
                return
            else:
                string = "Desc '%s' not found." % lhs
                caller.msg(msghead(self.sysname,error=True) + string)
                return
            