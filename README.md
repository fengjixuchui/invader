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

<img width="1440" alt="sas1" src="https://user-images.githubusercontent.com/43011806/61638217-3f17aa00-ac99-11e9-8fec-f090ca5c6ddc.png">

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

<img width="1440" alt="sas1" src="https://user-images.githubusercontent.com/43011806/61594387-90696000-abeb-11e9-8ec8-1625cc6d6998.png">

## Building powershell listener

> Invader

    (Invader)> listeners
    (Invader: listeners)> uselistener http
    (Invader: listeners/http)> execute
    (Invader: listeners/http)> launcher powershell
    
## Building python listener

> invader

    (Invader)> listeners
    (Invader: listeners)> uselistener http
    (Invader: listeners/http)> execute
    (Invader: listeners/http)> launcher python

## Interacting with a session

    INFO: After capturing a remote connection, you 
    need to select an open session to interact with it.

> invader 

    (Invader: listeners/http)> agents
    (Invader: agents)> interact <MachineName>
    (Invader: MachineName)> rename comp1
    (Invader: comp1)> info

# Why Invader framework?

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
    
<img width="1440" alt="sas3" src="https://user-images.githubusercontent.com/43011806/61594588-c871a280-abed-11e9-9d1e-3690bb16721c.png">

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
