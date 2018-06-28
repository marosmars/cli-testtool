import os
import shlex
import MockSSH
import sys
import time
from threading import Thread

from twisted.conch import avatar, interfaces as conchinterfaces, recvline
from twisted.conch import manhole
from twisted.conch.insults import insults
from twisted.internet.protocol import ClientFactory, ServerFactory
from twisted.conch.telnet import TelnetTransport, TelnetProtocol, AuthenticatingTelnetProtocol, ITelnetProtocol, TelnetBootstrapProtocol, StatefulTelnetProtocol
from twisted.conch.openssh_compat import primes
from twisted.conch.ssh import (connection, factory, keys, session, transport,
                               userauth)
from twisted.cred import checkers, portal
from twisted.internet import reactor
from zope.interface import implements

class ShowCommand(MockSSH.SSHCommand):

    def __init__(self, name, data, cmd_delay, *args):
        self.name = name
        self.data = data
        self.cmd_delay = cmd_delay
        self.required_arguments = [name] + list(args)
        self.protocol = None  # set in __call__

    def __call__(self, protocol, *args):
        if self.cmd_delay is not 0:
            print "Sleeping for %f seconds" % (self.cmd_delay / 1000.0)
            time.sleep(self.cmd_delay / 1000.0)

        MockSSH.SSHCommand.__init__(self, protocol, self.name, *args)
        return self

    def start(self):
        noArgs = (len(self.args[1:]) == 0) and (len(self.required_arguments[1:]) == 0)
        if (noArgs or " ".join(self.args[1:]) in set(self.required_arguments[1:])):
            self.writeln(self.data[" ".join(self.args)])
        else:
            self.writeln("% Invalid input")

        self.exit()

class PromptChangingCommand(MockSSH.SSHCommand):

    def __init__(self, name, newprompt, cmd_delay):
        self.name = name
        self.newprompt = newprompt
        self.cmd_delay = cmd_delay
        self.protocol = None  # protocol is set by __call__

    def __call__(self, protocol, *args):
        if self.cmd_delay is not 0:
            print "Sleeping for %f seconds" % (self.cmd_delay / 1000.0)
            time.sleep(self.cmd_delay / 1000.0)

        MockSSH.SSHCommand.__init__(self, protocol, self.name, *args)
        return self

    def start(self):
        self.protocol.prompt = self.newprompt
        self.exit()

class SimplePromptingCommand(MockSSH.SSHCommand):

    def __init__(self,
                 name,
                 password,
                 prompt,
                 newprompt,
                 error_msg,
                 cmd_delay):
        self.name = name
        self.valid_password = password
        self.prompt = prompt
        self.newprompt = newprompt
        self.error_msg = error_msg
        self.cmd_delay = cmd_delay

        self.protocol = None  # protocol is set by __call__

    def __call__(self, protocol, *args):
        MockSSH.SSHCommand.__init__(self, protocol, self.name, *args)
        return self

    def start(self):
        if self.cmd_delay is not 0:
            print "Sleeping for %f seconds" % (self.cmd_delay / 1000.0)
            time.sleep(self.cmd_delay / 1000.0)

        self.write(self.prompt)
        self.protocol.password_input = True

    def lineReceived(self, line):
        self.validate_password(line.strip())

    def validate_password(self, password):
        if password == self.valid_password:
            self.protocol.prompt = self.newprompt
        else:
            self.writeln(error_msg)

        self.protocol.password_input = False
        self.exit()


def getTelnetFactory(commands, prompt, **users):
    if not users:
        raise SSHServerError("You must provide at least one "
                             "username/password combination "
                             "to run this Telnet server.")
    cmds = {}
    for command in commands:
        cmds[command.name] = command
    commands = cmds

    for exit_cmd in ['_exit', 'exit']:
        if exit_cmd not in commands:
            commands[exit_cmd] = MockSSH.command_exit

    telnetRealm = _StupidRealm(TelnetBootstrapProtocol, prompt, commands)
 
    telnetPortal = portal.Portal(telnetRealm, (checkers.InMemoryUsernamePasswordDatabaseDontUse(**users),))
    telnetPortal.registerChecker(checkers.InMemoryUsernamePasswordDatabaseDontUse(**users))
    
    telnetFactory = ServerFactory()
    telnetFactory.protocol = makeTelnetProtocol(telnetPortal, telnetRealm, users)

    return telnetFactory
    
class _StupidRealm:
 
    def __init__(self, proto, prompt, commands):
        self.prompt = prompt
        self.commands = commands
        self.protocolFactory = proto
 
    def requestAvatar(self, avatarId, *interfaces):
        if ITelnetProtocol in interfaces:
            try:
                args = (avatarId, self.prompt, self.commands,)
                server = TelnetBootstrapProtocol(insults.ServerProtocol, TelnetProtocol, *args)
                return ITelnetProtocol, server, lambda: None
            except Exception as e:
                print e
        raise NotImplementedError()

class makeTelnetProtocol:
    def __init__(self, portal, telnetRealm, users):
        self.telnetRealm = telnetRealm
        self.users = users
        self.portal = portal
 
    def __call__(self):
        auth = AuthenticatingTelnetProtocol
        #auth = telnet.StatefulTelnetProtocol
        args = (self.portal,)
        return TelnetTransport(auth, *args)


# This is a copy paste of MockSSH.SSHProtocol changed to work on top of Manhole
class TelnetProtocol(manhole.Manhole):

    def __init__(self, user, prompt, commands):
        self.user = user
        self.prompt = prompt
        self.commands = commands
        self.password_input = False
        self.cmdstack = []

    def connectionMade(self):
        manhole.Manhole.connectionMade(self)
        self.cmdstack = [MockSSH.SSHShell(self, self.prompt)]

    def lineReceived(self, line):
        if len(self.cmdstack):
            self.cmdstack[-1].lineReceived(line)
        else:
            manhole.Manhole.lineReceived(self, line)

    def connectionLost(self, reason):
        manhole.Manhole.connectionLost(self, reason)
        del self.commands

    # Overriding to prevent terminal.reset() and setInsertMode()
    def initializeScreen(self):
        pass

    def getCommand(self, name):
        if name in self.commands:
            return self.commands[name]

    def keystrokeReceived(self, keyID, modifier):
        manhole.Manhole.keystrokeReceived(self, keyID, modifier)

    # Easier way to implement password input?
    def characterReceived(self, ch, moreCharactersComing):
        # manhole.Manhole.characterReceived(self, ch, moreCharactersComing)
        self.lineBuffer[self.lineBufferIndex:self.lineBufferIndex + 1] = [ch]
        self.lineBufferIndex += 1

        if not self.password_input:
            self.terminal.write(ch)

    def writeln(self, data):
        self.terminal.write(data)
        self.terminal.nextLine()

    def call_command(self, cmd, *args):
        obj = cmd(self, cmd.name, *args)
        self.cmdstack.append(obj)
        obj.start()

    def handle_RETURN(self):
        if len(self.cmdstack) == 1:
            if self.lineBuffer:
                self.historyLines.append(''.join(self.lineBuffer))
            self.historyPosition = len(self.historyLines)
        return manhole.Manhole.handle_RETURN(self)