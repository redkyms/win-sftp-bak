# win-sftp-bak 
Backup files and folders on Windows automatically via SFTP using 7-Zip.  
Script supports key authentication, as well as username/password authentication.  
 
# Requirements
Script requires at least: 
- Python 3 
- PIP 
- Modules listed in *requirements.txt* 
- Microsoft Windows (on source machine) 
- Linux (on target machine)
- 7-Zip

To get these modules, use PIP: 
 
```bash
pip install -r requirements.txt
```

Porting to Linux on source machine should be possible by redefining paths to certain executables and temp directory, however functions regarding to services should be either commented out, or changed to use e.g. systemctl.

# Connection data, backup path 
Before deploying this script, make sure to change connection data, source and destination paths.  
You can do that by opening *sftp-backup.py* in any text editor.  
Variables requiring your attention are available in self.ftp and self.win dictionaries, in the init function.  
Script also supports backup rotation. Change self.days variable in init accordingly.  
 
# Running the script 
To run the script, enter commandline (either cmd.exe or powershell.exe) and execute:
```batch
python path\to\script\sftp-backup.py
```
 
# Alerts, exit codes
E-mail alerts are currently not supported.  
Stdout informs user of taken actions, and stderr reports errors.  
If script ran successfully, it returns **0**. Otherwise, it returns **2**.  
