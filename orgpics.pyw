import os
import exifread
import hashlib
from PIL import Image
import time
import shutil
from multiprocessing import *
data = {'msg' : [], 'files' :0, 'pool_size':0, 'file_idx':0, 'procs':0, 'copy':0}

class OrgPics:
    #lock = Lock()
    def __init__(self, input_f, output_f='', data=data, gui=False):
        self.starttime = time.time()
        self.input_f = input_f
        self.output_f = output_f
        self.data = data
        self.gui = gui
        self.fhashs = []
        self.organize = True
        
        if output_f == '':
            self.organize = False
            self.duplicates = os.path.join(input_f, 'duplicates')
            self.new_location = self.duplicates
        else:
            self.duplicates = os.path.join(output_f, 'duplicates')
            self.dateless = os.path.join(output_f, 'dateless')
                
        if self.organize:
            self.prnt('Organize is called\n')
            self.makedir(output_f)
        
    def __call__(self):
        self.run()
        
    def run(self):
        self.prnt('starting orgpics process\nInput folder %s\nOutput folder %s\n'
                  %(self.input_f, self.output_f))
        self.copy = self.data['copy']
        files = 0
        loops = 0
        while(True):
            self.walk(first_time=True)
            self.callmulti_process()
            files += self.data['files']
            loops += 1
            if (self.flist == [] and self.organize) or  \
               (self.rmlist == [] and not self.organize) or \
                loops > 3 or self.copy:
                break
           
        self.data['files'] = files
        self.prnt('%d files processed in %d seconds\n'%(self.data['files'], 
                                                  time.time()- self.starttime))
    def walk(self, first_time=False):
        ''' Walks the input folder, and if first_time is ture, search for image
            files and add them to flist.
            Also remove empty folders
        '''
        def jpegsearch(dirname, files):
            for fname in files:
                if fname[-3:] in ['jpg', 'JPG']:
                    self.flist.append(os.path.normpath(os.path.join(dirname, fname)))
                    self.data['files'] += 1
        self.rmlist = []
        self.flist = []
        self.data['step'] = 1
        self.data['files'] = 0
        for (dirname, subshere, fileshere) in os.walk(self.input_f):
            # skip duplicates folder
            if dirname == self.duplicates: continue
                                       
            # search for jpeg files and add them to flist       
            jpegsearch(dirname, fileshere)
                        
            # remove picasa.ini and other files if exists
            rm_files = ['.picasa.ini', 'ZbThumbnail.info', 'Thumbs.db']
            for file in fileshere:
                if file in rm_files or file[-3:] in ['THM']:
                    os.remove(os.path.join(dirname, file))
                
            # remove folder if empty
            if not os.listdir(dirname):
                self.rmlist.append(dirname)
        if self.rmlist:
            self.rm_empty_folders()
        
        
    def prnt(self, msg):
       #self.lock.acquire() 
       if self.gui:
           self.data['msg'].append(msg)
       else:
           msg = msg[0:-1]
           print(msg)
       #self.lock.release()
       
    def rm_empty_folders(self):
        # remove empty folders
        self.prnt("removing empty folders %s\n"%self.rmlist)
        for d in self.rmlist:
            try:
                os.rmdir(d)
            except Exception as e:
                self.prnt('Error %s unable to remove folder %s\n'%(e,d))
                self.rmlist.remove(d)
        
    def callmulti_process(self):
        if not self.flist: return
        if self.data['procs']:
            MAX_POOL = self.data['procs']
        else:
            MAX_POOL = cpu_count() * 2
        files = len(self.flist)
        self.data['files'] = files
        if files < MAX_POOL:
            MAX_POOL = files
        self.data['pool_size'] = MAX_POOL
        self.data['step'] = 2
        self.prnt('Pool size is %d\n' %MAX_POOL)
        with Pool(MAX_POOL) as p:
            
            results = [p.apply_async(self.processfile, (f,), 
                                     callback=self.prnt) for f in self.flist]
            for i, r in enumerate(results):
                r.wait(1000)
                self.data['file_idx'] = i
                
    def processfile(self, file):
        self.file_path = file
        msg = 'pid:%s, processing file:%s\n'% ( os.getpid(), self.file_path)
        self.checkDuplicates()

        if self.organize and not self.isduplicate:
            # extract metadata from file
            msg = 'Org ' + msg
            self.extractOriginalDate()

            # move file to new location
            self.moveFile()
            
            # remove source file folder if empty
            dirname = os.path.dirname(self.file_path)
            if not os.listdir(dirname):
                try:
                    os.rmdir(dirname)
                except Exception as e:
                    self.prnt('Error 2 %s unable to remove folder %s'%(e, dirname))
        return msg
    
    def extractOriginalDate(self):
        # open image file for reading (binary mode)
        fh = open(self.file_path, 'rb')
        
        # Return Exif tags
        tags = exifread.process_file(fh)
        try:
            dto = tags['EXIF DateTimeOriginal']
        except KeyError:
            try:
                dto = tags['Image DateTime']
            except KeyError:
                self.new_location = self.dateless
                return
                
        # extract original date from metadata
        year = dto.__str__()[:4]
        month = dto.__str__()[5:7]
        day = dto.__str__()[8:10]
        
        self.new_location = os.path.normpath(os.path.join(self.output_f, year, 
                                               '%s-%s-%s' %(year, month, day)))
    
    def checkDuplicates(self):
        fhash = self.hashi()

        # extract dirname from file path
        dirname = os.path.dirname(self.file_path)
        
        #check to see if we have the file already
        if fhash in self.fhashs:
            # we have a possible file duplicate since the dto exists already
            # move to duplicates folder
            self.new_location = os.path.join(self.duplicates, dirname)
            self.moveFile()
            self.isduplicate = True
        else:
            self.isduplicate = False
            self.fhashs.append(fhash)
        
    def makedir(self, folder):
        '''
        create a folder if it does not exist 
        '''
        if not os.path.exists(folder):
            try:
                os.mkdir(folder)
            except Exception as e:
                self.prnt('Error %s Unable to create folder %s'%(e, folder))
        
    def moveFile(self):
        ymd_folder = self.new_location
        y_folder = os.path.dirname(ymd_folder)
        
        self.makedir(y_folder) 
        self.makedir(ymd_folder) 
            
        npl = os.path.join(ymd_folder, os.path.basename(self.file_path))
        
        if os.path.exists(npl) and not self.copy:
            try:
                os.remove(self.file_path) 
            except Exception as e:
                self.prnt('Error during remove %s'%e)
        else:
            try:
                if self.copy:
                    op = 'copy'
                    shutil.copy(self.file_path, npl)
                else:
                    op = 'move'
                    shutil.move(self.file_path, npl)
            except Exception as e:
                self.prnt('Error during %s %s'%(op,e))
        
    def hashi(self):
        tf = Image.open(self.file_path)
        return hashlib.md5(tf.tobytes()).hexdigest()
     
if __name__ == '__main__':
    import sys
    args = len(sys.argv)
    default_path = r'C:\Users\juju\Pictures'
    print('sys.argv ', sys.argv, 'args ', args)
    
    if len(sys.argv) > 2:
        op = OrgPics(input_f=sys.argv[1], output_f=sys.argv[2])
    elif len(sys.argv) == 2:
        op = OrgPics(input_f=sys.argv[1])
    else:
        op = OrgPics(input_f=default_path)
    op.run()
        
