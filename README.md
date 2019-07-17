# Invader (Windows/Linux/OSX agent)

    ________                    _________            
    ____  _/_________   _______ ______  /____________
     __  / __  __ \_ | / /  __ `/  __  /_  _ \_  ___/
    __/ /  _  / / /_ |/ // /_/ // /_/ / /  __/  /    
    /___/  /_/ /_/_____/ \__,_/ \__,_/  \___//_/ 
    
***

# About invader

    INFO: Invader (Windows/Linux/OSX agent)
    is a post exploitation framework that includes 
    a pure-PowerShell2.0 Windows agent,and a pure 
    Python 2.6/2.7 Linux/OSX agent.
    
***

# How to install invader

> cd invader/setup

> chmod +x install.sh

> ./install.sh

***

# How to build listener

    INFO: Invader listener is intended to capture 
    the remote connection to the victim's computer.

## Windows listener

> invader

    (Invader)> listeners
    (Invader: listeners)> uselistener http
    (Invader: listeners/http)> execute
    (Invader: listeners/http)> launcher powershell
    
## Linux listener

> invader

    (Invader)> listeners
    (Invader: listeners)> uselistener http
    (Invader: listeners/http)> execute
    (Invader: listeners/http)> launcher python
    
***

# Interacting with a session

    INFO: After capturing a remote connection, you 
    need to select an open session to interact with it.

> invader 

    (Invader: listeners/http)> agents
    (Invader: agents)> interact <MachineName>
    (Invader: MachineName)> rename comp1
    (Invader: comp1)> info

***

# Terms of use

    This tool is only for educational purposes only.
    Use this tool wisely and never without permission.
    I am not responsible for anything you do with this tool.

***

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
    
***

# Thats all!

    

