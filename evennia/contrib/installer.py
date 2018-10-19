from subprocess import call

import os
import logging, sys
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s():%(lineno)s] %(message)s", stream=sys.stdout)

import platform

#
# -----------------------------------------------------------------------------
#

PROJECT_NAME = 'demo'

#
# -----------------------------------------------------------------------------
#

WORKSPACE_NAME = 'mud_devel'
VIRTUALENV_NAME = PROJECT_NAME.upper()[:5]
REPO_URL = 'https://github.com/evennia/evennia.git'

#
# -----------------------------------------------------------------------------
#

class Installer(object):
    
    def __init__(self):
        logger = logging.getLogger(__name__)
        logger.info("Starting %s installer..." % self.__class__.__name__)
        self.home = self.identify_home()
        self.interpreter_path = sys.executable
    
    def install(self):
        logger = logging.getLogger(__name__)
        
        try:
            self.make_workspace()
            logger.info("Created workspace '%s'." % self.workspace_path)
        except Exception as exc:
            logger.error("Could not create workspace: %s" % exc)
            return False
        
        try:
            self.create_virtualenv()
            logger.info("Created virtual environment '%s' in '%s'." % (VIRTUALENV_NAME, self.virtualenv_path))
        except Exception as exc:
            logger.error("Could not create virtual environment: %s" % exc)
            return False
        
        try:
            self.clone_repo()
            logger.info("Cloned Evennia repository to '%s'." % self.local_repo_path)
        except Exception as exc:
            logger.error("Could not clone Evennia repository: %s" % exc)
            return False
        
        try:
            self.install_evennia()
            logger.info("Installed Evennia.")
        except Exception as exc:
            logger.error("Could not install Evennia: %s" % exc)
            return False
        
        try:
            self.create_game()
            logger.info("Created new game instance in '%s'." % self.project_path)
        except Exception as exc:
            logger.error("Could not create a new game instance: %s" % exc)
            return False
            
        logger.info("Installation complete!")
        return True
        
    @classmethod
    def identify_platform(cls):
        return platform.system()
        
    @classmethod
    def identify_home(cls):
        return os.path.expanduser("~")
    
    def make_workspace(self):
        logger = logging.getLogger(__name__)
        self.workspace_path = os.path.join(self.identify_home(), WORKSPACE_NAME)
        logger.debug(self.workspace_path)
        
        # Check if workspace path exists
        if os.path.exists(self.workspace_path):
            raise Exception("The '%s' workspace already exists." % WORKSPACE_NAME)
        
        os.mkdir(self.workspace_path)
        
    def create_virtualenv(self):
        logger = logging.getLogger(__name__)
        
        self.virtualenv_path = os.path.join(self.workspace_path, VIRTUALENV_NAME)
        logger.debug(self.virtualenv_path)
        
        # Check if virtualenv path exists
        if os.path.exists(self.virtualenv_path):
            raise Exception("Virtualenv '%s' already exists." % VIRTUALENV_NAME)
        
        call(['virtualenv', '-p', self.interpreter_path, self.virtualenv_path])
        
        self.virtual_interpreter = os.path.join(self.virtualenv_path, 'bin/python')
        logger.debug(self.virtual_interpreter)
        
        # Check if interpreter exists
        if not os.path.exists(self.virtual_interpreter):
            raise Exception("No Python binary/executable was found in '%s'." % self.virtual_interpreter)
        
    def clone_repo(self):
        logger = logging.getLogger(__name__)
        
        self.local_repo_path = os.path.join(self.workspace_path, 'evennia')
        logger.debug(self.local_repo_path)
        
        args = ['git', 'clone', REPO_URL, self.local_repo_path]
        logger.debug(' '.join(args))
        
        call(args)
        
    def install_evennia(self):
        logger = logging.getLogger(__name__)
        
        self.pip_path = os.path.join(self.virtualenv_path, 'bin/pip')
        logger.debug(self.pip_path)
        
        # Check if pip exists
        if not os.path.exists(self.pip_path):
            raise Exception("No pip binary was found in '%s'." % (self.pip_path))
        
        install_args = [self.pip_path, 'install', '-e', self.local_repo_path]
        logger.debug(' '.join(install_args))
        
        call(install_args)
        
    def create_game(self):
        logger = logging.getLogger(__name__)
        
        self.evennia_bin_path = os.path.join(self.virtualenv_path, 'bin/evennia')
        logger.debug(self.evennia_bin_path)
        
        # Check if Evennia exists
        if not os.path.exists(self.evennia_bin_path):
            raise Exception("No Evennia binary was found in '%s'." % self.evennia_bin_path)
        
        self.project_path = os.path.join(self.workspace_path, PROJECT_NAME)
        logger.debug(self.project_path)
        
        # Check if project exists
        if os.path.exists(self.project_path):
            raise Exception("A game already exists in '%s'." % self.project_path)
        
        game_args = [self.evennia_bin_path, '--init', self.project_path]
        logger.debug(' '.join(game_args))
        call(game_args)
        
class Windows(Installer):
    pass

class Linux(Installer):
    pass

class Apple(Installer):
    pass

if __name__ == "__main__":
    # Get platform
    env = Installer.identify_platform()
    
    if env == 'Windows':
        Windows().install()
    elif env == 'Linux':
        Linux().install()
    else:
        Apple().install()