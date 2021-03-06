import httplib2
import json
import time
import subprocess
import datetime
import base64
import paramiko
import sys
import os
import getpass
import errno

from socket import error as socket_error
import socket

# this should be your home folder
homeFolder = "/home/gary"

# when authCache is set to True, your account credentials will be saved in ~/.weaved/auth
# if you don't want this to happen, keep authcache as False
authcache = False
authCacheFile="~/.weaved/auth"

# for P2P connections we have the ability to maintain the port assignment for a given UID (deviceaddress)
portCache = True;
portCacheFile=homeFolder + "/.weaved/endpoints"

# sshCache will store your SSH credentials per device so you don't have to re-enter them each time
sshCache=True;
sshCacheFile = homeFolder + "/.weaved/ssh"

# deviceList File is the list of UIDs you wish to scan through - in this case they should be configured for SSH
deviceListFile = homeFolder + "/.weaved/devicelist"

# remoteScriptFile is the script you want to have executed on the target device.
# this is just like any shell script with two additions:
# @fileSend source target - sends a file from the source to the remote device
# @fileGet source target - gets a file from the source (remote device) to the target (local device)

remoteScriptFile = homeFolder + "/.weaved/remotescript"

apiMethod="http://"
apiVersion="/v21"
apiServer="api.weaved.com"
apiKey="WeavedDemoKey$2015"
# for production, remove these and ask the user at the begnning of the session
userName = ""
password = ""
deviceName=""
# substitute the name of the actual daemon you are using.
# this will depend on CPU architecture and OS details
clientDaemon = "/usr/bin/weavedConnectd.linux"

#===============================================
def getPort(UID, name):
    if(portCache == True):
        startPort = 33000
        cacheHit = False
        if(os.path.isfile(portCacheFile)):
            with open(portCacheFile, 'r') as f:
                for line in f:
                    params = line.split("|")
                    port = params[0].split("TPORT")[1]
                    if(startPort < port):
                        startPort = port
#                        print startPort
                    if(UID in line):
                        assignedPort = port
                        cacheHit = True
                        break
        if(cacheHit == False):
            assignedPort = int(startPort) + 1
            print "Caching port for", UID
            with open(portCacheFile, 'a') as f:
                f.write("TPORT%d" % assignedPort + "|"  + name + "|"  + UID + "\n")
    return int(assignedPort)

#===============================================
def p2pConnect(startPortNum, startDaemon):
#   uncomment the following line to force proxy mode connections
    return (-1,0)
    portNum = getPort(deviceItem["deviceaddress"], deviceItem["devicealias"])                
    print "Device:", deviceItem["devicealias"]
    if(startDaemon == True):
        portParam = "T%d" % int(portNum)
        args = [clientDaemon, "-l", "5000", "hello", "-c", base64userName, base64password, deviceItem["deviceaddress"], portParam, "1", "127.0.0.1", "12"]
    #    print args
        try:
            proc = subprocess.Popen(args,shell=False)
        except:
            "Process launch exception!"
#    Listen to UDP port 5000 to get the ready status or error messages
    statusPort = 5000
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("", statusPort))
    while 1:    # debug status scan from daemon
        data, addr = s.recvfrom(128)
# uncomment the following statement to see all output from the daemon
#        print data
        if 'hello Proxy started.' in data:
            break
        if 'hello Cannot Bind Port' in data:
            print 'Cannot bind to port: ', portNum
            return (-1, -1)
        if 'hello weavedConnectd terminated' in data:
            print 'P2P connection timed out!', portNum
            return (-1, -1)
    ssh = trySSHConnect('127.0.0.1', portNum)
    return (ssh, proc)

#===============================================
from urllib2 import urlopen
from json import dumps
from json import load

def proxyConnect(UID, token):
    print "Entering proxyConnect()"
    # my_ip = urlopen('http://ip.42.pl/raw').read()
    my_ip = load(urlopen('http://jsonip.com'))['ip']
    print "my_ip =", my_ip

    proxyConnectURL = apiMethod + apiServer + apiVersion + "/api/device/connect"

    proxyHeaders = {
                'Content-Type': content_type_header,
                'apikey': apiKey,
                'token': token
            }

    proxyBody = {
                'deviceaddress': UID,
                'hostip': my_ip,
                'wait': "true"
            }

    response, content = http.request( proxyConnectURL,
                                          'POST',
                                          headers=proxyHeaders,
                                          body=dumps(proxyBody),
                                       )
#    print "Response = ", response
    print "Content = ", content

    data = json.loads(content)["connection"]["proxy"]
    URI = data.split(":")[0] + ":" + data.split(":")[1]
    URI = URI.split("://")[1]
    portNum = data.split(":")[2]

    print "URI = ", URI
    print "Port = ", portNum
    
    ssh = trySSHConnect(URI, int(portNum))
    return ssh

#===============================================
def trySSHConnect(host, portNum):
# initiate Paramiko SSH session Ex
    sshUserName, sshPassword = getSSHCredentials()
    paramiko.util.log_to_file ('paramiko.log') 

#and then check the response...
    try:
        ssh = paramiko.SSHClient()
        print "1"
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print "2"
# was trying to add banner_timeout because it seems to have that failure
# occasionally. Couldn't get it working.
#        ssh.connect(host, port=portNum, username=sshUserName,
#            password=sshPassword, pkey=None, key_filename=None,
#            timeout=3.0, allow_agent=True, look_for_keys=True,
#            compress=False, sock=None, gss_auth=False, gss_kex=False,
#            gss_deleg_creds=True, gss_host=None, banner_timeout=5.0)
        print "hostname = ", host
        print "port = ", portNum
        print "sshUsername = ", sshUserName
        print "sshPassword = ", sshPassword

        ssh.connect(hostname=host, port=portNum, username=sshUserName, password=sshPassword)
        print "3"
        ssh.get_transport().window_size = 3 * 1024 * 1024
        print "4"
    except paramiko.AuthenticationException:
        print "Authentication failed!"
        return -1
    except paramiko.BadHostKeyException:
        print "BadHostKey Exception!"
        return -1
    except paramiko.SSHException:
        print "SSH Exception!"
        ssh.close()
        return -2
    except socket.error as e:
        print "Socket error ", e
        return -1
    except:
        print "Could not SSH to %s, unhandled exception" % host
    print "Made connection to " + host + ":" + str(portNum)
    return (ssh)

#===============================================
def getSSHCredentials():
    cacheHit = False
    if(os.path.isfile(sshCacheFile)):
        with open(sshCacheFile, 'r') as f:
            UID = deviceItem["deviceaddress"]
#            print UID
            for line in f:
                if(UID in line):
                    params = line.split("|")
                    sshUserName = params[1]
                    sshPassword = params[2]
                    cacheHit = True
                    break
            if(cacheHit == False):
                sshUserName = raw_input("SSH user name:") 
                sshPassword = raw_input("SSH password:")
                with open(sshCacheFile, 'a') as f:
                    f.write(deviceItem["deviceaddress"] + "|" + sshUserName + "|" + sshPassword + "|\n")
    else:
        sshUserName = raw_input("SSH user name:") 
        sshPassword = raw_input("SSH password:")                  
        with open(sshCacheFile, 'a') as f:
            f.write(deviceItem["deviceaddress"] + "|" + sshUserName + "|" + sshPassword + "|\n")
    return (sshUserName, sshPassword)

#===============================================
def remoteScript(ssh):
    if(os.path.isfile(remoteScriptFile)):
        channel = ssh.invoke_shell(term='vt100', width=80, height=24)
        
        fileHandle = open(remoteScriptFile, 'r')
        for line in fileHandle:
            lineBits = line.split(" ")
            # handle special file transfer command
            if("@fileSend" == lineBits[0]):
                source = lineBits[1]
                target = lineBits[2]
                sendFile(ssh, source, target)
            if("@fileGet" == lineBits[0]):
                source = lineBits[1]
                target = lineBits[2]
                # this line is putting the retrieved file in a certain place and naming it with the target device name (alias)
                # you may choose to change this to anything you want
                getFile(ssh, source, '/home/gary/Desktop/' + deviceItem["devicealias"] + target)
            else:
#                print line
                channel.send(line)
# this delay is used on slower devices to allow all commands to get to log file
        time.sleep(3)
#        output=channel.recv(8000)
#        print(output)
    else:
        print "Remote script file does not exist!"
        print "Please create a script file at:", remoteScriptFile
        
#===============================================
   
def sendFile(ssh, source, target):
    try:
        ftp = ssh.open_sftp()
    except paramiko.ssh_exception.SSHException, e:
            print "SSH Exception on opening sftp connection\n", e
    else:
        #====== now retrieve the remote file and place on desktop
        print "Send", source, "to", target
        ftp.put(source, target)
        ftp.close() 

#===============================================

def getFile(ssh, source, target):
    try:
        ftp = ssh.open_sftp()
    except paramiko.ssh_exception.SSHException, e:
            print "SSH Exception on opening sftp connection\n", e
    else:
        #====== now retrieve the remote file and place on desktop
        print "Get", source, "to", target
        ftp.get(source, target)
        ftp.close() 


#===============================================
if __name__ == '__main__':

    httplib2.debuglevel     = 0
    http                    = httplib2.Http()
    content_type_header     = "application/json"


    loginURL = apiMethod + apiServer + apiVersion + "/api/user/login"

#    print "Login URL = " + loginURL

    loginHeaders = {
                'Content-Type': content_type_header,
                'apikey': apiKey
            }
    try:        
        response, content = http.request( loginURL + "/" + userName + "/" + password,
                                          'GET',
                                          headers=loginHeaders)
    except:
        print "Server not found.  Possible connection problem!", e
        exit()
                                          
#    print (response)
    print "============================================================"
#    print (content)
    print

    try: 
        data = json.loads(content)
        if(data["status"] != "true"):
            print "Can't connect to Weaved server!"
            print data["reason"]
            exit()

        token = data["token"]
    except KeyError:
        print "Comnnection failed!"
        exit()
#    except URLError:
#        print "Connection failed!"
#        exit()
        
    print "Token = " +  token

    deviceListURL = apiMethod + apiServer + apiVersion + "/api/device/list/all"

    deviceListHeaders = {
                'Content-Type': content_type_header,
                'apikey': apiKey,
                'token': token,
            }
            
    response, content = http.request( deviceListURL,
                                          'GET',
                                          headers=deviceListHeaders)
    print "----------------------------------" 

    deviceData = json.loads(content)
#    print deviceData["devices"]
    base64userName = base64.b64encode(userName)
    base64password = base64.b64encode(password)
    portNum = 33000

    # iterate on the device names in the deviceFile
    fileHandle = open(deviceListFile, 'r')
    for line in fileHandle:
        deviceName = line.split("|")[0]
        foundDevice = False
        # now iterate over all devices in returned list
        for deviceItem in deviceData["devices"]:
            if(deviceItem["devicealias"] == deviceName):
                foundDevice = True
                if(deviceItem["devicestate"] == "active"):
                    # attempt P2P connection after starting daemon
                    ssh, proc = p2pConnect(portNum, True)
                    # -2 indicates SSH Exception, commonly failure to retrievebanner
                    if(ssh == -2):
                        print "Retrying P2P..."
                        # ssh.close()
                        # attempt P2P without starting daemon (presumed started)
                        ssh, proc = p2pConnect(portNum, False)                 
                    if(ssh > 0):
                        print "Executing script via P2P."
                        remoteScript(ssh)
                        ssh.close()
                        proc.kill()
                    else:
                        print "Trying proxy connection to %s." % deviceItem["devicealias"]
                        ssh = proxyConnect(deviceItem["deviceaddress"], token)
                        if(ssh != -1):
                            print "Executing script via proxy."
                            remoteScript(ssh)
                            ssh.close()
                        else:
                            print "Proxy connection failed!"
                    portNum = portNum + 1
                    print "----------"
        if foundDevice == False:
            print"Could not find ", deviceName


