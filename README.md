# Invader Framework (Remote Administration Tool)
        
    ________                    _________           
    ____  _/_________   _______ ______  /____________   
     __  / __  __ \_ | / /  __ `/  __  /_  _ \_  ___/    
    __/ /  _  / / /_ |/ // /_/ // /_/ / /  __/  /        
    /___/  /_/ /_/_____/ \__,_/ \__,_/  \___//_/     

</a>
<h4 align="center">Details</h4>                
<p align="center">
  <a href="http://entynetproject.simplesite.com/">
    <img src="https://img.shields.io/badge/entynetproject-Ivan%20Nikolsky-blue.svg">
  </a> 
  <a href="https://github.com/entynetproject/Invader/releases">
    <img src="https://img.shields.io/github/release/entynetproject/Invader.svg">
  </a>
  <a href="https://ru.m.wikipedia.org/wiki/python">
    <img src="https://img.shields.io/badge/language-python-blue.svg">
 </a>
  <a href="https://github.com/entynetproject/Invader">
    <img src="https://img.shields.io/badge/tool-RAT-red.svg">
 </a>
  <a href="https://github.com/entynetproject/Invader/issues?q=is%3Aissue+is%3Aclosed">
      <img src="https://img.shields.io/github/issues/entynetproject/Invader.svg">
  </a>
  <a href="https://github.com/entynetproject/Invader/wiki">
      <img src="https://img.shields.io/badge/wiki%20-Invader-lightgrey.svg">
 </a>
  <a href="https://mobile.twitter.com/entynetproject">
    <img src="https://img.shields.io/badge/twitter-entynetproject-blue.svg">
 </a>
</p>

<img width="1440" alt="alias" src="https://user-images.githubusercontent.com/43011806/62296271-07fe8100-b46f-11e9-9691-c9fb2e192b33.png">

# About invader framework

    INFO: Invader Framework is a post exploitation framework 
    that includes a pure-PowerShell2.0 Windows and a pure 
    Python 2.6/2.7 Linux/OSX Remote Administration Tool.

# How to install invader

> cd invader/setup

> chmod +x install.sh

> ./install.sh

<img width="1440" alt="sas2" src="https://user-images.githubusercontent.com/43011806/61594477-ab889f80-abec-11e9-9f94-7065bdede64b.png">

# How to uninstall invader

> cd invader/setup

> chmod +x uninstall.sh

> ./uninstall.sh

    INFO: You should know that after uninstalling 
    Invader all files of this framework will removed!

# Invader framework examples

<img width="1440" alt="invader" src="https://user-images.githubusercontent.com/43011806/63594254-4393f300-c5b6-11e9-8481-211e4f0f431e.png">

## Building powershell listener

> invader

        (Invader)> listeners
    [!] No listeners currently active 
    (Invader: listeners)> listener http
    (Invader: listeners/http)> info
    
        Name: HTTP[S]
    Category: client_server

    Authors:
      @harmj0y

    Description:
      Starts a http[s] listener (PowerShell or Python) that uses a
      GET/POST approach.

    HTTP[S] Options:

      Name              Required    Value                            Description
      ----              --------    -------                          -----------
      payloadURI        False                                        URI for the payload. Must use /download/. Example: /download/payload.php
      ProxyCreds        False       default                          Proxy credentials ([domain\]username:password) to use for request (default, none, or other).
      KillDate          False                                        Date for the listener to exit (MM/dd/yyyy).
      Name              True        http                             Name for the listener.
      SlackToken        False                                        Your SlackBot API token to communicate with your Slack instance.
      Launcher          True        powershell -noP -sta -w 1 -enc   Launcher string.
      DefaultDelay      True        5                                Agent delay/reach back interval (in seconds).
      DefaultLostLimit  True        60                               Number of missed checkins before exiting
      WorkingHours      False                                        Hours for the agent to operate (09:00-17:00).
      DefaultProfile    True        /admin/get.php,/news.php,/login/ Default communication profile for the agent.
                                process.php|Mozilla/5.0 (Windows
                                NT 6.1; WOW64; Trident/7.0;
                                rv:11.0) like Gecko
      Host              True                                         Hostname/IP for staging.
      CertPath          False                                        Certificate path for https listeners.
      DefaultJitter     True        0.0                              Jitter in agent reachback interval (0.0-1.0).
      Proxy             False       default                          Proxy to use for request (default, none, or other).
      UserAgent         False       default                          User-agent string to use for the staging request (default, none, or other).
      StagingKey        True        a684eceee76fc522773286a895bc8436 Staging key for initial agent negotiation.
      BindIP            True        0.0.0.0                          The IP to bind to on the control server.
      Port              True                                         Port for the listener.
      ServerVersion     True        Microsoft-IIS/7.5                Server header for the control server.
      SlackChannel      False       #general                         The Slack channel or DM that notifications will be sent to.


    (Invader: listeners/http)> set Host <lhost>
    (Invader: listeners/http)> set Port <lport>
    (Invader: listeners/http)> execute
    [*] Starting listener 'http'
     * Serving Flask app "http" (lazy loading)
     * Environment: production
       WARNING: This is a development server. Do not use it in a production deployment.
       Use a production WSGI server instead.
     * Debug mode: off
    [+] Listener successfully started!
    (Invader: listeners/http)> launcher powershell
    
## Building python listener

> invader

    (Invader)> listeners
    [!] No listeners currently active 
    (Invader: listeners)> listener http
    (Invader: listeners/http)> info
    
        Name: HTTP[S]
    Category: client_server

    Authors:
      @harmj0y

    Description:
      Starts a http[s] listener (PowerShell or Python) that uses a
      GET/POST approach.

    HTTP[S] Options:

      Name              Required    Value                            Description
      ----              --------    -------                          -----------
      payloadURI        False                                        URI for the payload. Must use /download/. Example: /download/payload.php
      ProxyCreds        False       default                          Proxy credentials ([domain\]username:password) to use for request (default, none, or other).
      KillDate          False                                        Date for the listener to exit (MM/dd/yyyy).
      Name              True        http                             Name for the listener.
      SlackToken        False                                        Your SlackBot API token to communicate with your Slack instance.
      Launcher          True        powershell -noP -sta -w 1 -enc   Launcher string.
      DefaultDelay      True        5                                Agent delay/reach back interval (in seconds).
      DefaultLostLimit  True        60                               Number of missed checkins before exiting
      WorkingHours      False                                        Hours for the agent to operate (09:00-17:00).
      DefaultProfile    True        /admin/get.php,/news.php,/login/ Default communication profile for the agent.
                                process.php|Mozilla/5.0 (Windows
                                NT 6.1; WOW64; Trident/7.0;
                                rv:11.0) like Gecko
      Host              True                                         Hostname/IP for staging.
      CertPath          False                                        Certificate path for https listeners.
      DefaultJitter     True        0.0                              Jitter in agent reachback interval (0.0-1.0).
      Proxy             False       default                          Proxy to use for request (default, none, or other).
      UserAgent         False       default                          User-agent string to use for the staging request (default, none, or other).
      StagingKey        True        a684eceee76fc522773286a895bc8436 Staging key for initial agent negotiation.
      BindIP            True        0.0.0.0                          The IP to bind to on the control server.
      Port              True                                         Port for the listener.
      ServerVersion     True        Microsoft-IIS/7.5                Server header for the control server.
      SlackChannel      False       #general                         The Slack channel or DM that notifications will be sent to.


    (Invader: listeners/http)> set Host <lhost>
    (Invader: listeners/http)> set Port <lport>
    (Invader: listeners/http)> execute
    [*] Starting listener 'http'
     * Serving Flask app "http" (lazy loading)
     * Environment: production
       WARNING: This is a development server. Do not use it in a production deployment.
       Use a production WSGI server instead.
     * Debug mode: off
    [+] Listener successfully started!
    (Invader: listeners/http)> launcher python

## Interacting with a session

    INFO: After capturing a remote connection, you 
    need to select an open session to interact with it.

> invader 

    (Invader)> agents
    
    [*] Active agents:

     Name     La Internal IP     Machine Name      Username                Process            PID    Delay    Last Seen
     ----     -- -----------     ------------      --------                -------            ---    -----    ---------
     K6SHX6MX py 192.168.2.100   MacBook-Pro       Enty8080                /usr/bin/python    39763  5/0.0    2019-08-23 15:56:07
     
     (Invader: agents)> interact K6SHX6MX

# Why invader framework?

> A lot of Remote Administration Tool modules

    INFO: Invader Framework has a lot of python 
    and powershell modules for full remote control!
    
> Simple UX/UI interface for beginners

    INFO: Invader has simple UX/UI for beginners!
    It is easy to understand and it will be easier 
    for you to master the Invader Framework.
    
> Remote Administration Tool (RAT)

    INFO: Control your computer remotely using only 
    Invader Framework Remote Administration Tool.
    
<img width="1440" alt="sas2" src="https://user-images.githubusercontent.com/43011806/61638872-99653a80-ac9a-11e9-924a-fa08137a4d22.png">

# System requirements

> python2

    INFO: You can install it with apt-get install python2

> python2-pip

    INFO: You can install it with apt-get install python2-pip

# Terms of use

    This tool is only for educational purposes only.
    Use this tool wisely and never without permission.
    I am not responsible for anything you do with this tool.

# Invader MIT license

    MIT License

    Copyright (C) 2019, Entynetproject. All Rights Reserved.

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.

# Thats all!
