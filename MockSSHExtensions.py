import os
import shlex
import MockSSH
import sys
import time
from threading import Thread

from twisted.conch import avatar, interfaces as conchinterfaces, recvline
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


# Telnet attempt

class TelnetPrinter(TelnetProtocol):
  def dataReceived(self, bytes):
      print 'Received:', repr(bytes)

class TelnetFactory(ClientFactory):
  def buildProtocol(self, addr):
      args = (self.portal,)
      return TelnetTransport(AuthenticatingTelnetProtocol, *args)


def getTelnetFactory(commands, prompt, **users):
    if not users:
        raise SSHServerError("You must provide at least one "
                             "username/password combination "
                             "to run this SSH server.")

    cmds = {}
    for command in commands:
        cmds[command.name] = command
    commands = cmds

    for exit_cmd in ['_exit', 'exit']:
        if exit_cmd not in commands:
            commands[exit_cmd] = MockSSH.command_exit

    # sshFactory = factory.SSHFactory()
    #sshFactory = TelnetFactory()

    telnetPortal = portal.Portal(
        _StupidRealm(TelnetBootstrapProtocol, prompt, commands), [checkers.InMemoryUsernamePasswordDatabaseDontUse(**users)])
    telnetPortal.registerChecker(
        checkers.InMemoryUsernamePasswordDatabaseDontUse(**users))

    telnetFactory = ServerFactory()
    telnetFactory.protocol = makeTelnetProtocol(telnetPortal)

    return telnetFactory
    

class makeTelnetProtocol:
    def __init__(self, portal):
        self.portal = portal
 
    def __call__(self):
        #auth = AuthenticatingTelnetProtocol
        auth = StatefulTelnetProtocol
        args = (self.portal,)
        return TelnetTransport(auth, *args)


class _StupidRealm:
 
    def __init__(self, proto, prompt, commands):
        self.prompt = prompt
        self.commands = commands
        self.protocolFactory = proto
 
    def requestAvatar(self, avatarId, *interfaces):
        if ITelnetProtocol in interfaces:
            try:
                print "aaa"
                return ITelnetProtocol, insults.ServerProtocol(SSHProtocol, self, self.prompt, self.commands), lambda: None
            except Exception as e:
                print e
        raise NotImplementedError()


class SSHProtocol(recvline.HistoricRecvLine):

    def __init__(self, user, prompt, commands):
        print "a"
        self.user = user
        self.prompt = prompt
        self.commands = commands
        self.password_input = False
        self.cmdstack = []

    def connectionMade(self):
        print "b"

        recvline.HistoricRecvLine.connectionMade(self)
        self.cmdstack = [SSHShell(self, self.prompt)]

        transport = self.terminal.transport.session.conn.transport
        transport.factory.sessions[transport.transport.sessionno] = self
        # p = self.terminal.transport.session.conn.transport.transport.getPeer()
        # self.client_ip = p.host

        self.keyHandlers.update({
            '\x04': self.handle_CTRL_D,
            '\x15': self.handle_CTRL_U,
            '\x03': self.handle_CTRL_C,
        })

    def lineReceived(self, line):
        if len(self.cmdstack):
            self.cmdstack[-1].lineReceived(line)

    def connectionLost(self, reason):
        recvline.HistoricRecvLine.connectionLost(self, reason)
        del self.commands

    # Overriding to prevent terminal.reset() and setInsertMode()
    def initializeScreen(self):
        pass

    def getCommand(self, name):
        if name in self.commands:
            return self.commands[name]

    def keystrokeReceived(self, keyID, modifier):
        recvline.HistoricRecvLine.keystrokeReceived(self, keyID, modifier)

    # Easier way to implement password input?
    def characterReceived(self, ch, moreCharactersComing):
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
        return recvline.HistoricRecvLine.handle_RETURN(self)

    def handle_CTRL_C(self):
        self.cmdstack[-1].ctrl_c()

    def handle_CTRL_U(self):
        for i in range(self.lineBufferIndex):
            self.terminal.cursorBackward()
            self.terminal.deleteCharacter()
        self.lineBuffer = self.lineBuffer[self.lineBufferIndex:]
        self.lineBufferIndex = 0

    def handle_CTRL_D(self):
        self.call_command(self.commands['_exit'])