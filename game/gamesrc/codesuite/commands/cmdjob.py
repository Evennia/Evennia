import re, ev, datetime, string, math
from .. command import MuxCommand
from src.players.models import PlayerDB
from src.utils import utils, gametime,ansi
from .. lib.align import PrettyTable
from .. lib.penn import header,table,msghead,STAFFREP
from .. lib.charmatch import charmatch
from .. lib.EVJobs.models import JobCat,Job,JobComment,JobLog,JobRead,JobVote
from .. lib.align import PrettyTable
from django.db.models import Q

class CmdJob(MuxCommand):
    """
    +job is used to contact the Storytellers with things you need.
    Jobs are labeled into CATEGORIES, such as BUILD or XP, to help staff know
    who ought to handle what job and what priority it should be.
    
    For all commands that don't directly modify a category's properties,
    <category> can partial match - but as always, be careful with such.
    
    Note: Jobs use the Player/account system, not characters, for their names.
    
    Admin may see all +jobs, players may only see their own and ones they've
    been appointed to handle by admin.

    +job/categories
    Show what categories may be posted to.

    +job [<ID>]
    By itself, shows recent jobs. Giving an ID shows that job's details.
    
    +job page=<#>
    Shows other pages of jobs.

    +job/add <category>/<title>=<text>
    +job/add <category>=<text>
    Creates a new +job for Storytellers. It will display to them live that
    you have done so, and you will receive updates as they work on it.
    The first syntax sets a custom job title to display, the second uses the
    first few words of <text> as <title>. It's strongly recommended that 
    character names feature in <titles> for relevant jobs like XP processing.

    +job/comment <ID>=<text>
    Appends a comment to a job, used to add or revise new information to it.
    Warning: To prevent shenanigans, comments may never be edited or deleted
    in any fashion.

    +job/vote <ID>=<vote>
    Players may vote on any job they can see, aside from their own. This only
    occurs if a player is made handler of another person's job or a category.
    <vote> may be Yes, No, or Undecided.

    +job/log <ID>
    Shows a log of events that happened to a Job.

    *STAFF ONLY*
    +job/claim <ID>[=<player>]
    Assigns a job to <player>, or yourself if <player> is not given.
    
    +job/delete <ID>
    Obviously, deletes a job. Jobs should be retained for book-keeping, but use
    this when necessary.
    
    +job/approve <ID>=<text>
    +job/deny <ID>=<text>
    +job/revive <ID>=<text>
    Approves or denies a Job, preventing further actions to be taken on it.
    Use Revive to return a job to pending status if necessary. <text> will be
    included similar to a comment.

    * Legend for +job display-
    * - Updates or changes made since you last checked the job.
    P - Job is pending.
    A - job was approved.
    D - job was denied.
    """
    
    key = "+job"
    locks = "cmd:all()"
    sysname = "JOB"
    help_category = "Player"
    
    def func(self):
        caller = self.caller
        switches = self.switches
        rhs = self.rhs
        lhs = self.lhs
        isadmin = self.isadmin
        playswitches = ['add','comment','log','vote']
        admswitches = ['catmake','catdelete','catrename','catvisible','catpriority',
                       'approve','deny','revive''claim','approve','deny','revive']
        
        if isadmin:
            callswitches = playswitches + admswitches
        else:
            callswitches = playswitches
        switches = self.partial(switches,callswitches)
        
        if lhs.lower() == "page" and re.match('^[\d]+$', rhs):
            self.showpage = int(rhs)
        else:
            self.showpage = 1
            
        if not switches and re.match('^[\d]+$', lhs):
            self.switch_showjob(lhs)
        elif not switches:
            self.switch_showall(self.showpage)
        elif 'catmake' in switches and isadmin:
            self.switch_catmake(lhs)
        elif 'catdelete' in switches and isadmin:
            self.switch_catdelete(lhs)
        elif 'catrename' in switches and isadmin:
            self.switch_catrename(lhs,rhs)
        elif 'catvisible' in switches and isadmin:
            self.switch_catvisible(lhs)
        elif 'catpriority' in switches and isadmin:
            self.switch_catvisible(lhs)
        elif 'categories' in switches:
            self.switch_categories()
        elif 'add' in switches:
            self.switch_add(lhs,rhs)
        elif 'claim' in switches and isadmin:
            self.switch_claim(lhs,rhs)
        elif 'comment' in switches:
            self.switch_comment(lhs,rhs)
        elif 'vote' in switches:
            self.switch_vote(lhs,rhs)
        elif 'log' in switches:
            self.switch_log(lhs)
        elif 'approve' in switches and isadmin:
            self.switch_approve(lhs,rhs)
        elif 'deny' in switches and isadmin:
            self.switch_deny(lhs,rhs)
        elif 'revive' in switches and isadmin:
            self.switch_revive(lhs,rhs)
        else:
            self.switch_showall(self.showpage)

    def verify_catname(self,lhs):
        if not lhs:
            string = "Category name field empty."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return False
        if not re.match('^[\w]+$', lhs):
            string = "Category names may only use alphanumeric characters."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return False
        if len(lhs) > 10:
            string = "Category names may not exceed 10 characters in length."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return False
        return True

    def switch_catmake(self,lhs):
        if not self.verify_catname(lhs):
            return
        catsearch = JobCat.objects.filter(key__iexact=lhs)
        if len(catsearch):
            string = "That category already exists."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        newcat = JobCat(key=lhs.upper())
        newcat.save()
        string = "Job category '%s' created!" % newcat.key
        self.caller.msg(msghead(self.sysname) + string)
        
    def switch_catdelete(self,lhs):
        if not self.verify_catname(lhs):
            return
        catsearch = JobCat.objects.filter(key__iexact=lhs)
        if not len(catsearch):
            string = "That category does not exist."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        catsearch.delete()
        string = "Job category '%s' deleted!" % lhs
        self.caller.msg(msghead(self.sysname) + string)
        
    def switch_catrename(self,lhs,rhs):
        if not self.verify_catname(lhs):
            return
        catsearch = JobCat.objects.filter(key__iexact=lhs)
        if not len(catsearch):
            string = "That category does not exist."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        if not self.verify_catname(rhs):
            return
        catsearch[0].key = rhs
        catsearch[0].save()
        string = "Job category '%s' renamed to %s!" % (lhs.upper(),rhs)
        self.caller.msg(msghead(self.sysname) + string)

    def switch_categories(self):
        self.caller.msg("CATEGORIES: %s" % ", ".join(JobCat.objects.values_list('key',flat=True)))

    def get_jobs(self,jstatus=None,page=None,cat=None):
        if self.isadmin:
            jobs = Job.objects.order_by('id').reverse()
        else:
            jobs = Job.objects.filter(Q(submitter=self.player.dbobj) | Q(handlers=self.player.dbobj)).order_by('id').reverse()
        if page is None:
            return jobs
        else:
            startjob = (page * 30) - 30
            endjob = (page * 30)
            return jobs[startjob:endjob]

    def switch_showall(self,showpage):
        self.caller.msg(header("Pending Jobs"))
        jobs = self.get_jobs(page=showpage)
        self.show_jobs(jobs)
        alljobs = self.get_jobs(page=None)
        pages = int(math.ceil(len(alljobs) / 30.0))
        self.caller.msg(header("Showing Page %s of %s" % (showpage,pages)))
        
    def show_jobs(self,jobs):
        if not len(jobs):
            self.caller.msg(msghead(self.sysname) + "No jobs to show.")
            return
        jobtable = PrettyTable(["*","Job#","Cat","Title","By","Handler","Added","Cmts"])
        jobtable.border = False
        jobtable.align = "l"
        jobtable.max_width["*"] = 2
        jobtable.max_width["Job#"] = 4
        jobtable.max_width["Cat"] = 6
        jobtable.max_width["Title"] = 20
        jobtable.max_width["By"] = 15
        jobtable.max_width["Handler"] = 15
        jobtable.max_width["Added"] = 10
        jobtable.max_width["Cmts"] = 3
        for job in jobs:
            handlers = []
            for handler in job.handlers.all():
                handlers.append(handler.key)
            jread = JobRead.objects.filter(reader=self.player.dbobj,jobid=job)
            if len(jread):
                if jread[0].readdate < job.updated:
                    statusmark = "*"
                else:
                    statusmark = job.status
            else:
                statusmark = "*"
            jobtable.add_row([statusmark,job.id,job.jobcat.key,job.jobtitle,job.submitter.key,
                             ", ".join(handlers),job.submitted.strftime('%b %d'),
                             len(JobComment.objects.filter(jobid=job.id))])
        self.caller.msg(jobtable)
        
    def switch_add(self,lhs,rhs):
        if "/" in lhs:
            catname,jtitle = lhs.split("/",1)
        else:
            catname = lhs
        if not self.verify_catname(catname):
            return
        catsearch = JobCat.objects.filter(key__istartswith=catname)
        if not len(catsearch):
            string = "Category '%s' not found." % catname
            self.caller.msg(msghead(self.sysname,error=True) + string)
        catsearch = catsearch[0]
        if not rhs:
            string = "Job text field empty."
            self.caller.msg(msghead(self.sysname,error=True) + string)
        if jtitle:
            jtitle = jtitle[:25]
        else:
            jtitle = rhs[:25]
        newjob = Job(jobcat=catsearch,priority=catsearch.priority,
                     submitter=self.player.dbobj,
                     jobtitle=ansi.parse_ansi(jtitle,strip_ansi=True),jobtext=rhs)
        newjob.save()
        self.update_jobread(newjob,self.player)
        # reminder to put an alert here
        string = "Job submitted!"
        self.caller.msg(msghead(self.sysname) + string)
        self.caller.execute_cmd("+job %s" % newjob.id)
        self.make_log(newjob,self.player,"Created job.")
        #cemit(STAFFREP,"{w%s{n submitted %s Job %s: %s" % (self.player.key,newjob.jobcat,newjob.id,newjob.jobtitle))

    def update_jobread(self,job,player):
        newread, created = JobRead.objects.get_or_create(jobid=job,reader=player.dbobj)
        newread.save()
        
    def target_job(self,job,message):
        if not job:
            self.caller.msg(msghead(self.sysname,error=True) + message)
            return
        jobs = self.get_jobs()
        if not len(jobs):
            string = "No jobs in the system."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        job = jobs.filter(pk=job)
        if not len(job):
            string = "Job does not exist."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        return job[0]

    def job_viable(self,job):
        if job.status == " ":
            return True
        elif job.status == "D":
            string = "That job was Denied!"
        elif job.status == "A":
            string = "That job was Approved!"
        self.caller.msg(msghead(self.sysname,error=True) + string)
        return False
        
    def switch_showjob(self,lhs):
        job = self.target_job(lhs,"No Job entered to display!")
        if not job:
            return
        self.caller.msg(header("%s Job %s: %s" % (job.jobcat.key,job.id,job.jobtitle)))
        if job.status == " ":
            status = "Pending"
        elif job.status == "A":
            status = "Approved"
        elif job.status == "D":
            status = "Denied"
        handlers = []
        for handler in job.handlers.all():
            handlers.append(handler.key)
        
        line1 = string.ljust("  {cCreator:{n %s" % job.submitter.key,45) + "{cCreated:{n %s" % job.submitted.strftime('%b %d')
        line2 = string.ljust("   {cStatus:{n %s" % status,44) + "{cHandlers:{n %s" % ", ".join(handlers)
        line3 = "  {cDetails:{n %s" % job.jobtext
        self.caller.msg("\n".join([line1,line2,line3]))
        comments = JobComment.objects.filter(jobid=job)
        for comment in comments:
            self.caller.msg("\n".join([header("%s Added on %s" % (comment.submitter.key,comment.submitted.ctime())),comment.commenttext]))
        if len(JobVote.objects.filter(jobid=job)):
            self.caller.msg(header("Votes"))
            yescount = JobVote.objects.filter(jobid=job,vote__iexact="Yes").count()
            yesstring = "Yes: %s" % yescount
            yesplyrs = JobVote.objects.filter(jobid=job,vote__iexact="Yes")
            yesnames = []
            for vote in yesplyrs:
                yesnames.append(vote.voter.key)
            nocount = JobVote.objects.filter(jobid=job,vote__iexact="No").count()
            nostring = "No: %s" % nocount
            noplyrs = JobVote.objects.filter(jobid=job,vote__iexact="No")
            nonames = []
            for vote in noplyrs:
                nonames.append(vote.voter.key)
            uncount = JobVote.objects.filter(jobid=job,vote__iexact="Undecided").count()
            unstring = "Undecided: %s" % uncount
            unplyrs = JobVote.objects.filter(jobid=job,vote__iexact="Undecided")
            unnames = []
            for vote in unplyrs:
                unnames.append(vote.voter.key)
            if yescount:
                self.caller.msg(yesstring)
                self.caller.msg(", ".join(yesnames))
            if nocount:
                self.caller.msg(nostring)
                self.caller.msg(", ".join(nonames))
            if uncount:
                self.caller.msg(unstring)
                self.caller.msg(", ".join(unnames))
        self.caller.msg(header())
        self.update_jobread(job,self.player)

    def switch_log(self,lhs):
        job = self.target_job(lhs,"No Job entered to examine!")
        if not job:
            return
        self.caller.msg(header("%s Job(Log) %s: %s" % (job.jobcat.key,job.id,job.jobtitle)))
        logs = JobLog.objects.filter(jobid=job)
        for log in logs:
            self.caller.msg("\n".join(["{wFrom %s on %s:{n" % (log.submitter.key,log.submitted.ctime()),log.logtext]))
        self.caller.msg(header())

    def switch_comment(self,lhs,rhs,):
        job = self.target_job(lhs,"No Job entered to comment on!")
        if not job:
            return
        if not self.job_viable(job):
            return
        if not rhs:
            string = "Comment text field empty."
            self.caller.msg(msghead(self.sysname,error=True) + string)
        newcomment = JobComment(jobid=job,submitter=self.player.dbobj,commenttext=rhs)
        newcomment.save()
        self.update_jobread(job,self.player)
        # alert goes here.
        string = "Your comment has been submitted."
        self.caller.msg(msghead(self.sysname) + string)
        job.save()
        self.make_log(job,self.player,"Added comment.")
        string = "{w%s{n commented on %s Job %s: %s" % (self.player.key,job.jobcat,job.id,job.jobtitle)
        self.send_alert(job,string)

    def switch_vote(self,lhs,rhs):
        job = self.target_job(lhs,"No Job entered to vote on!")
        if not job:
            return
        if not self.job_viable(job):
            return
        if not (self.player.dbobj in job.handlers.all() or self.isadmin):
            string = "You may not vote on your own jobs."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        if not rhs:
            string = "Vote text field empty."
            self.caller.msg(msghead(self.sysname,error=True) + string)
        if not rhs.lower() in ['yes','no','undecided']:
            string = "Votes may only be yes, no, or undecided."
            self.caller.msg(msghead(self.sysname,error=True) + string)
        newvote,created = JobVote.objects.get_or_create(jobid=job,voter=self.player.dbobj)
        newvote.vote = rhs
        newvote.save()
        job.save()
        self.update_jobread(job,self.player)
        self.make_log(job,self.player,"Voted %s" % rhs)
        string = "{w%s{n Voted '%s' on %s Job %s: %s" % (self.player.key,rhs.upper(),job.jobcat,job.id,job.jobtitle)
        self.send_alert(job,string)
        
    def switch_claim(self,lhs,rhs):
        if not lhs:
            string = "No Job entered to claim!"
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        job = Job.objects.get(pk=lhs)
        if not job:
            string = "Job not found."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        if not self.job_viable(job):
            return
        if self.player.dbobj in job.handlers.all() and not rhs:
            string = "You are already a handler for this job."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        if rhs:
            target = ev.search_player(rhs)
            if target:
                target = target[0]
            else:
                string = "Player '%s' not found." % rhs
                self.caller.msg(msghead(self.sysname,error=True) + string)
                return
        else:
            target = self.player
        if target in job.handlers.all():
            string = "Player '%s' is already a Handler." % target.key
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        job.handlers.add(target.dbobj)
        job.save()
        string = "%s added to handlers for Job %s: %s" % (target.key,job.id,job.jobtitle)
        self.caller.msg(msghead(self.sysname) + string)
        self.make_log(job,target,"Added %s to Handlers" % target.key)
        string = "{w%s{n added {w%s{n to handlers for Job %s: %s" % (self.player.key,target.key,job.id,job.jobtitle)
        self.send_alert(job,string)
        
    def switch_approve(self,lhs,rhs,):
        job = self.target_job(lhs,"No Job entered to approve!")
        if not job:
            return
        if not self.job_viable(job):
            return
        if rhs:
            extratext = "%s\n\nThe Job was Approved." % rhs
        else:
            extratext = "The Job was Approved."
        newcomment = JobComment(jobid=job,submitter=self.player.dbobj,commenttext=extratext)
        newcomment.save()
        job.status = "A"
        self.update_jobread(job,self.player)
        # alert goes here.
        string = "You approved the job."
        self.caller.msg(msghead(self.sysname) + string)
        job.save()
        self.make_log(job,self.player,"Job was approved.")
        string = "{w%s{n approved %s Job %s: %s" % (self.player.key,job.jobcat,job.id,job.jobtitle)
        self.send_alert(job,string)

    def switch_deny(self,lhs,rhs):
        job = self.target_job(lhs,"No Job entered to deny!")
        if not job:
            return
        if not self.job_viable(job):
            return
        if rhs:
            extratext = "%s\n\nThe Job was Denied." % rhs
        else:
            extratext = "The Job was Denied."
        newcomment = JobComment(jobid=job,submitter=self.player.dbobj,commenttext=extratext)
        newcomment.save()
        job.status = "D"
        self.update_jobread(job,self.player)
        # alert goes here.
        string = "You denied the job."
        self.caller.msg(msghead(self.sysname) + string)
        job.save()
        self.make_log(job,self.player,"Job was denied.")
        string = "{w%s{n denied %s Job %s: %s" % (self.player.key,job.jobcat,job.id,job.jobtitle)
        self.send_alert(job,string)
        
    def switch_revive(self,lhs,rhs,):
        job = self.target_job(lhs,"No Job entered to revive!")
        if not job:
            return
        if job.status == " ":
            string = "Can only revive Approved or Denied jobs."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        if rhs:
            extratext = "%s\n\nThe Job was Revived." % rhs
        else:
            extratext = "The Job was Revived."
        newcomment = JobComment(jobid=job,submitter=self.player.dbobj,commenttext=extratext)
        newcomment.save()
        job.status = " "
        self.update_jobread(job,self.player)
        # alert goes here.
        string = "You revived the job."
        self.caller.msg(msghead(self.sysname) + string)
        job.save()
        self.make_log(job,self.player,"Job was revived.")
        string = "{w%s{n revived %s Job %s: %s" % (self.player.key,job.jobcat,job.id,job.jobtitle)
        self.send_alert(job,string)
        
    def make_log(self,job,player,message):
        newlog = JobLog(jobid=job,submitter=player.dbobj,logtext=message)
        newlog.save()
        
    def send_alert(self,job,message):
        job.submitter.msg(msghead(self.sysname) + message)
        for handler in job.handlers.all():
            handler.msg(msghead(self.sysname) + message)
        #cemit(STAFFREP,message)
