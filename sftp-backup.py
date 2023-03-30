from subprocess import run
from time import sleep
import datetime
import win32serviceutil
import os
import scp
import paramiko

class Backup():

    def __init__(self):

        self.ftp = {
            "address": "changeme", #ssh server's ip address
            "username": "changeme",
            "password": "changeme",
            "path": "/changeme/", #path on the remote server
            "port": 22,
            "timeout": 60.0, #ssh timeout in seconds
            "private_key": None,
            #if using key authentication: supply absolute path to the .pem file in self.ftp['private_key'] variable (other formats (e.g. putty's .ppk) are not supported by paramiko)
            #if the file is encrypted, self.ftp['password'] variable supplies password to the given file and is required to connect successfully
            #if the file is not encrypted, change self.ftp['password'] variable to None
        }
        self.win = {
            "services": ["service1", "service2"], #services to start/stop during backup
            "zip": "C:\\Program Files\\7-Zip\\7z.exe", #path to 7z file executable
            "sources": "changeme",
            "temp": f"{os.getenv('TEMP')}\\sftp-backup",
            "prefix": "changeme", #backup zip file prefix - eg.: changeme_YYYY-MM-DDHHmmss.zip
        }

        self.dt = str(datetime.datetime.now().replace(microsecond=0))
        
        try:
            print("establishing connection to SSH server...")
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # can be dangerous against MiTM attacks. comment it out if necessary but make sure to manually add the remote host to known_hosts file before running the script
            if not self.ftp['private_key']:
                self.ssh.connect(hostname=self.ftp['address'],port=self.ftp['port'],username=self.ftp['username'],password=self.ftp['password'])
            elif self.ftp['private_key'] and self.ftp['password']:
                self.ssh.connect(hostname=self.ftp['address'],port=self.ftp['port'],username=self.ftp['username'],password=self.ftp['password'], key_filename=self.ftp['private_key'])
            else:
                self.ssh.connect(hostname=self.ftp['address'],port=self.ftp['port'],username=self.ftp['username'],key_filename=self.ftp['private_key'])
            print("connection established")
        except Exception as e:
            print("connection failed")
            print(e)
            exit(2)
        
        #delete backups older than:
        self.days = 14


    def cleanup(self, target, days):
        print(f'cleaning up backups older than {days} days')
        noop = ":"
        (stdin, stdout, stderr) = self.ssh.exec_command(noop) # get default stderr
        default_stderr = stderr.read()
        del stdin, stdout, stderr
        rm_command = f"find {target}/{self.win['prefix']}*.zip -maxdepth 1 -mtime +{days} -type f -delete"
        (stdin, stdout, stderr) = self.ssh.exec_command(rm_command)
        new_stderr = stderr.read()
        if not new_stderr == default_stderr:
            sanitized_stderr = (new_stderr[len(default_stderr):]).decode('utf-8') # strip default stderr from new stderr
            print("error during backup rotation")
            print(sanitized_stderr)
            return False
        return True

    def start_services(self):
        services = self.win['services']
        print(f"services scheduled for startup: {services}")
        for service in services:
            try:
                win32serviceutil.StartService(service)
            except:
                pass
            sleep(10) #windows services need some time to start/close after receiving signal - applying timeout to mitigate that
            self.verify_service_start(service) #and make sure the service really started!

    def start_service(self, service):
        print(f"trying to start service {service}")
        win32serviceutil.StartService(service)
        sleep(10)
    
    def verify_service_start(self, service):
        print(f"verifying if service {service} started successfully")
        query = win32serviceutil.QueryServiceStatus(service)
        if query[1] != 4:
            print(f"verification failed - service not running")
            for i in range(0,3,1):
                self.start_service(service)
        elif query[1] == 4:
            print(f"service {service} started successfully")
            return True

    def stop_services(self):
        services = self.win['services']
        print(f"services scheduled for shutdown: {services}")
        for service in services:
            try:
                win32serviceutil.StopService(service)
                print(f"successfully stopped service {service}")
            except:
                pass
            sleep(10)
            self.verify_service_stop(service)

    def stop_service(self, service):
        print(f"trying to stop service {service}")
        win32serviceutil.StopService(service)
        sleep(10)

    def verify_service_stop(self, service):
        query = win32serviceutil.QueryServiceStatus(service)
        if query[1] != 1:
            print(f"verification failed - service still running")
            for i in range(0,3,1):
                self.stop_service(service)
        elif query[1] == 1:
            print(f"service {service} stopped correctly")
            return True

    def ready_temp(self, dir):
        if (os.path.exists(dir)): #check if temp dir exists
            i = os.listdir(dir) #list files
            for item in i: #remove them
                if os.path.isfile(item):
                    os.remove(item)
        else: #otherwise lets create our own dir
            try:
                os.mkdir(dir)
                return True
            except Exception as e:
                print("couldn't create temp dir")
                print(e)
                return False

    def get_valid_filename(self):
        sanitized_dt = ((self.dt).replace(" ", "")).replace(":", "")
        filename = f"{self.win['prefix']}_{sanitized_dt}.zip"
        return filename
    
    def send_to_sftp(self, path):
        try:
            self.scp = scp.SCPClient(self.ssh.get_transport(), socket_timeout=self.ftp['timeout'])
            self.scp.put(path, recursive=False, remote_path=self.ftp['path'])
            print("files sent successfully")
        except Exception as e:
            print("error while sending files to sftp server")
            print(e)
        finally:
            if self.scp is not None:
                self.scp.close()
                del self.scp
            if self.ssh is not None:
                self.ssh.close()
                del self.ssh

    def zip(self):
        z = self.win['zip']
        name = self.get_valid_filename()
        fullpath = self.win['temp'] + "\\" + name
        source = self.win['sources']
        try:
            run([z, "a", "-y", "-mx5", fullpath, source], shell=True)
            return fullpath
        except Exception as e:
            print("couldn't create zip file")
            print(e)
            exit(2)

    def start(self):
        self.ready_temp(self.win['temp'])
        self.cleanup(self.ftp['path'], self.days)
        self.stop_services()
        p = self.zip()
        self.send_to_sftp(p)
        self.start_services()
        self.ready_temp(self.win['temp'])
        exit(0)
            


if __name__ == '__main__':
    a = Backup()
    a.start()
