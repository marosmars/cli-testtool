#!/usr/bin/python
#
"""
This is how it should be used:

hostname>en
Password:
hostname#conf t
Enter configuration commands, one per line. End with CNTL/Z
hostname(config)#username admin password secure
hostname(config)#exit
hostname#wr m
Building configuration...
[OK]
hostname#
"""

import sys, time
import MockSSH
import MockSSHExtensions
import traceback

import json
from collections import defaultdict

from twisted.python import log
from threading import Thread
from twisted.internet import reactor

from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory, ServerFactory
from twisted.conch.telnet import TelnetTransport, TelnetProtocol, AuthenticatingTelnetProtocol, ITelnetProtocol, TelnetBootstrapProtocol, StatefulTelnetProtocol
from twisted.cred import checkers, portal
from twisted.conch import avatar, interfaces as conchinterfaces, recvline
from twisted.conch import manhole
from twisted.conch.insults import insults
from twisted.conch.ssh import session
import multiprocessing
import subprocess

pool = None
batch_size = 100 # ports to handle per process

def main():

    # FIXME Make proper arguments
    port_low = int(sys.argv[2])
    port_high = int(sys.argv[3])
    all_ports = port_high - port_low

    last_batch = all_ports % batch_size
    processes = all_ports / batch_size

    protocol_type = sys.argv[4]
    device_file = sys.argv[5]
    interface = sys.argv[1]

    log.startLogging(sys.stdout)

    with open(device_file) as f:
        data = json.load(f)

    global pool
    process_pool_size = processes if last_batch <=0 else (processes + 1)
    print "Spawning pool with %s processes" % process_pool_size
    pool = multiprocessing.Pool(processes if last_batch <=0 else (processes + 1))

    args = []
    for i in range(0, processes):

        starting_port = port_low + i*batch_size
        ending_port = port_low + batch_size + i*batch_size
        print "Spawning process for ports: %s - %s" % (starting_port, ending_port)
        if i == processes - 1:
            ending_port = ending_port + 1

        args.append((starting_port, ending_port, interface, protocol_type, data))

    r = pool.map_async(spawn_server_wrapper, args)

    if last_batch > 0:
        starting_port = port_low + processes*batch_size + 1
        ending_port = port_high + 1
        print "Spawning process for ports: %s - %s" % (starting_port, ending_port)
        r2 = pool.map_async(spawn_server_wrapper, [(starting_port, ending_port, interface, protocol_type, data)])
        try:
            r2.wait()
        except KeyboardInterrupt:
            r.wait()

    r.wait()

def spawn_server_wrapper(args):
    spawn_server(*args)

def spawn_server(port_low, port_high, interface, protocol_type, data):

    for i in range(port_low, port_high):
        try:
            show_commands, prompt_change_commands, usr, passwd, cmd_delay, default_prompt = parse_commands(data)

            users = {usr : passwd}

            local_commands = []

            for cmd in show_commands:    
                command = getShowCommand(cmd, data, show_commands[cmd], cmd_delay)
                local_commands.append(command)

            for cmd in prompt_change_commands:
                if ("password" in prompt_change_commands[cmd]):
                    command = getPasswordPromptCommand(cmd, prompt_change_commands[cmd], cmd_delay)
                else:
                    command = getPromptChangingCommand(cmd, prompt_change_commands[cmd], cmd_delay)
                local_commands.append(command)


            factory = None
            if (protocol_type == "ssh"):
                factory = MockSSH.getSSHFactory(local_commands, default_prompt, ".", **users)
            elif (protocol_type == "telnet"):
                factory = MockSSHExtensions.getTelnetFactory(local_commands, default_prompt, **users)

            reactor.listenTCP(i, factory, interface=interface)

        except Exception as e:
            print >> sys.stderr, traceback.format_exc()
            print "Unable to open port at %s, due to: %s" % (i, e)

    reactor.run()


def parse_commands(data):
    show_commands = defaultdict(list)
    prompt_change_commands = {}

    default_prompt = data["setting_default_prompt"]
    cmd_delay = data["setting_cmd_delay"]

    usr = data["setting_default_user"]
    passwd = data["setting_default_passwd"]

    print "Using username: %s and password: %s" % (usr, passwd)

    for cmd in data:
        if isinstance(data[cmd], dict):
            prompt_change_commands[cmd] = data[cmd]
            print "Adding prompt changing command: %s" % cmd
        else:
            cmd_split = cmd.split(" ", 1)
            if (len(cmd_split) == 1):
                show_commands[cmd_split[0]]
            else:
                show_commands[cmd_split[0]].append(cmd_split[1])
            print "Adding show command: %s, with arguments: %s" % (cmd, show_commands[cmd])

    return (show_commands, prompt_change_commands, usr, passwd, cmd_delay, default_prompt)


def getPasswordPromptCommand(cmd, values, cmd_delay):
    return MockSSHExtensions.SimplePromptingCommand(values["name"],values["password"],values["prompt"],values["newprompt"],values["error_message"], cmd_delay)

def getPromptChangingCommand(cmd, values, cmd_delay):
    return MockSSHExtensions.PromptChangingCommand(cmd, values["newprompt"], cmd_delay)

def getShowCommand(cmd, data, arguments, cmd_delay):
    return MockSSHExtensions.ShowCommand(cmd, data, cmd_delay, *arguments)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print "User interrupted"
        global pool
        pool.close()
        pool.terminate()
        pool.join()
        sys.exit(1)
