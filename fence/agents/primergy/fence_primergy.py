#!/usr/bin/python

###############################################################################
###############################################################################
##
##  Copyright (C) 2006 Red Hat, Inc.  All rights reserved.
##
##  This copyrighted material is made available to anyone wishing to use,
##  modify, copy, or redistribute it subject to the terms and conditions
##  of the GNU General Public License v.2.
##
###############################################################################
###############################################################################


import getopt, sys
import os
import socket
import time

from telnetlib import Telnet

TELNET_TIMEOUT=30 #How long to wait for a response from a telnet try

# WARNING!! Do not add code bewteen "#BEGIN_VERSION_GENERATION" and
# "#END_VERSION_GENERATION"  It is generated by the Makefile

#BEGIN_VERSION_GENERATION
FENCE_RELEASE_NAME=""
REDHAT_COPYRIGHT=""
BUILD_DATE=""
#END_VERSION_GENERATION

def usage():
  print "Usage:\n"
  print "fence_primergy [options]\n"
  print "Options:\n"
  print "   -a <ipaddress>           ip or hostname of rsb\n"
  print "   -h                       print out help\n"
  print "   -l [login]               login name\n"
  print "   -p [password]            password\n"
  print "   -o [action]              Reboot (default), Off, On, or Status\n"
  print "   -v Verbose               Verbose mode\n"
  print "   -V                       Print Version, then exit\n"

  sys.exit (0)

def version():
  print "fence_primergy %s  %s\n" % (FENCE_RELEASE_NAME, BUILD_DATE)
  print "%s\n" % REDHAT_COPYRIGHT
  sys.exit(0)

def main():
  depth = 0
  POWER_OFF = 0
  POWER_ON = 1
  POWER_STATUS = 2
  POWER_REBOOT = 3

  address = ""
  login = ""
  passwd = ""
  action = POWER_REBOOT   #default action
  verbose = False

  standard_err = 2

  #set up regex list
  USERNAME = 0
  PASSWORD = 1
  PROMPT = 2
  STATE = 3
  ERROR = 4
  CONT = 5
  CONFIRM = 6
  DONE = 7

  regex_list = list()
  regex_list.append("user name\s*:")
  regex_list.append("pass phrase\s*:")
  regex_list.append("[Ee]nter\s+[Ss]election[^\r\n]*:")
  regex_list.append("[pP]ower Status:")
  regex_list.append("[Ee]rror\s*:")
  regex_list.append("[Pp]ress any key to continue")
  regex_list.append("[Dd]o you really want")
  regex_list.append("CLOSING TELNET CONNECTION")

  if len(sys.argv) > 1:
    try:
      opts, args = getopt.getopt(sys.argv[1:], "a:hl:o:p:vV", ["help", "output="])
    except getopt.GetoptError:
      #print help info and quit
      usage()
      sys.exit(2)

    for o, a in opts:
      if o == "-v":
        verbose = True
      if o == "-V":
        version()
      if o in ("-h", "--help"):
        usage()
        sys.exit()
      if o == "-l":
        login = a
      if o == "-p":
        passwd = a
      if o  == "-o":
        if a == "Off" or a == "OFF" or a == "off":
          action = POWER_OFF
        elif a == "On" or a == "ON" or a == "on":
          action = POWER_ON
        elif a == "Status" or a == "STATUS" or a == "status":
          action = POWER_STATUS
        elif a == "Reboot" or a == "REBOOT" or a == "reboot":
          action = POWER_REBOOT
        else:
          usage()
          sys.exit()
      if o == "-a":
        address = a
    if address == "" or login == "" or passwd == "":
      usage()
      sys.exit()

  else: #Take args from stdin...
    params = {}
    #place params in dict
    for line in sys.stdin:
      val = line.split("=")
      params[val[0]] = val[1]

    try:
      address = params["ipaddr"]
    except KeyError, e:
      os.write(standard_err, "FENCE: Missing ipaddr param for fence_primergy...exiting")
    try:
      login = params["login"]
    except KeyError, e:
      os.write(standard_err, "FENCE: Missing login param for fence_primergy...exiting")

    try:
      passwd = params["passwd"]
    except KeyError, e:
      os.write(standard_err, "FENCE: Missing passwd param for fence_primergy...exiting")

    try:
      a = params["option"]
      if a == "Off" or a == "OFF" or a == "off":
        action = POWER_OFF
      elif a == "On" or a == "ON" or a == "on":
        action = POWER_ON
      elif a == "Reboot" or a == "REBOOT" or a == "reboot":
        action = POWER_REBOOT
    except KeyError, e:
      action = POWER_REBOOT

    ####End of stdin section

  ##Time to open telnet session and log in. 
  try:
    sock = Telnet(address.strip(), 3172)
  except socket.error, (errno, msg):
    my_msg = "FENCE: A problem was encountered opening a telnet session with " + address
    os.write(standard_err, my_msg)
    os.write(standard_err, ("FENCE: Error number: %d -- Message: %s\n" % (errno, msg)))
    os.write(standard_err, "Firewall issue? Correct address?\n")
    sys.exit(1)

  if verbose:
    print  "socket open to %s\n" % address

  while 1:
    i, mo, txt = sock.expect(regex_list, TELNET_TIMEOUT)
    if i == ERROR:
      os.write(standard_err,("FENCE: An error was encountered when communicating with the rsb device at %s" % address))
      buf = sock.read_eager()
      os.write(standard_err,("FENCE: The error message is - %s" % txt + " " + buf))
      sock.close()
      sys.exit(1)

    buf = sock.read_eager()
    if i == USERNAME:
      if verbose:
        print "Sending login: %s\n" % login
      sock.write(login + "\r")

    elif i == PASSWORD:
      if verbose:
        print "Sending password: %s\n" % passwd
      sock.write(passwd + "\r")

    elif i == CONT:
      if verbose:
        print "Sending continue char..."
      sock.write("\r")
      time.sleep(2)

    elif i == CONFIRM:
      if verbose:
        print "Confirming..."
      sock.write("yes\r")

    elif i == PROMPT:
      if verbose:
        print "Evaluating prompt...\n"

      if depth == 0:
        sock.write("2\r")
      elif depth == 1:
        if action == POWER_OFF:
          if verbose:
            print "Sending power off command to %s\n" % address
          sock.write("1\r")
          time.sleep(2)

        elif action == POWER_ON:
          if verbose:
            print "Sending power on %s" % address
          sock.write("4\r")
          time.sleep(2)

        elif action == POWER_REBOOT:
          if verbose:
            print "Rebooting server..."
          sock.write("3\r")
          time.sleep(2)
      else:
        sock.write("0\r");
      depth += 1

    elif i == STATE and action == POWER_STATUS:
      if verbose:
        print "Determining power state..."
      if buf.find(" On") != (-1):
        print "Server is On"
      elif buf.find(" Off") != (-1):
        print "Server is off"
      elif verbose:
        print "Cannot determine power state: %s" % buf
      break

    elif i == DONE:
      break;

  sock.close()

if __name__ == "__main__":
  main()
