# This scrip will commit the latest changes, and then, push the changes to 
# remote server.
# Call the cr script to update the wsrepo on remote server.
import sys
import os
import glob

class PushProject:
    def __init__(self):
        self.toolsdir = os.path.dirname(os.path.abspath(__file__))
        self.base_path = os.path.split(self.toolsdir)[0]
        sys.path.append(self.toolsdir)
        os.chdir(self.base_path)
        
    def clean_files(self):
        for (dirname, subshere, fileshere) in os.walk(self.base_path):
            tempf = glob.glob('%s\*.py[co]'%dirname)
            if '.git' in dirname: continue
            if tempf: 
                for filen in tempf:
                    print ('deleting %s'%filen)
                    os.remove(filen)
            
    def get_git(self):
        print ("issue git command to remove unwated files")
        os.system(r'git rm *.py[oc]')
        
        print ("issue git command to add modified files")
        os.system(r'git add *')
        
        print ("issue git command to commit changes")
        comment = input('Enter a good description for your changes: ')
        os.system(r'git commit -m "%s"'%comment)

        print ("issue git command to push changes to server")
        os.system(r'git push')

        print ("issue git command to print status")
        os.system(r'git status')

        print ("issue git command to display log")
        os.system(r'git log --oneline')

    def delete_output():
        datadir = '_repo'
        output  = os.path.join(self.base_path, datadir)
        if os.path.exists(output):
            shutil.rmtree(output)
        os.chdir(os.path.join(self.base_path, self.toolsdir))
        
if __name__ == '__main__':
    pp = PushProject()
    pp.clean_files()
    pp.get_git()
    

