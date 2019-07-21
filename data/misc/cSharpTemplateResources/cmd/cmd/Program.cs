/*
 * 
 * You may compile this in Visual Studio or SharpDevelop etc.
 * 
 * 
 * 
 * 
 */
using System;
using System.Text;
using System.Management.Automation; 
using System.Management.Automation.Runspaces; 

namespace cmd
{
	class Program
	{
		public static void Main(string[] args)
		{
			string payload = " YOUR CODE GOES HERE";
			var decodedScript = Encoding.Unicode.GetString(Convert.FromBase64String(payload));

            Runspace runspace = RunspaceFactory.CreateRunspace();
            runspace.Open();
            RunspaceInvoke scriptInvoker = new RunspaceInvoke(runspace);
            Pipeline pipeline = runspace.CreatePipeline();

            pipeline.Commands.AddScript(decodedScript);

            pipeline.Commands.Add("Out-String");
            pipeline.Invoke();
        }
	}
}