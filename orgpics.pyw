import os
import exifread
import hashlib
from PIL import Image
import time
from multiprocessing import *
from socket_stream_redirect0 import redirectOut        # connect my sys.stdout to socket
data = {'msg' : [], 'files' :0, 'pool_size':0, 'file_idx':0}
class OrgPics:
    def __init__(self, input_f, output_f='', redirect = False, queue=None, data=data, gui=False):
        self.starttime = time.time()
        self.input_f = input_f
        print('input %s, output %s, redirect %s, queue %s, data %s' %(input_f, output_f, redirect, queue, data))
        self.output_f = output_f
        self.redirect = redirect
        self.queue = queue
        self.data = data
        self.gui = gui
        self.flist = []
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
        self.prnt('starting orgpics process\ninput folder %s\n'%self.input_f)            
        self.walk(first_time=True)
        self.callmulti_process3()
        self.prnt('%d files processed in %d seconds\n'%(self.data['files'], 
                                                  time.time()- self.starttime))
        for i in range(2):
            self.walk()
         
    def jpegsearch(self, dirname, files):
        for fname in files:
            if fname[-3:] in ('jpg', 'JPG'):
                self.flist.append(os.path.normpath(os.path.join(dirname, fname)))
                self.data['files'] += 1
                self.data['file_idx'] += 1
        
    def walk(self, first_time=False):
        ''' Walks the input folder, and if first_time is ture, search for image
            files and add them to flist.
            Also remove empty folders
        '''
        rmlist = []
        file_counter = 0
        for (dirname, subshere, fileshere) in os.walk(self.input_f):
            if first_time:
                # skip duplicates folder
                if dirname == self.duplicates: continue
                                           
                # search for jpeg files and add them to flist       
                self.jpegsearch(dirname, fileshere)
#            else:
#                self.prnt('dirname %s subs here %s\n'%(dirname, subshere))
                            
            # remove folder if empty
            if not os.listdir(dirname):
#                self.prnt("adding %s to remove list\n"%dirname)
                rmlist.append(dirname)
        if rmlist:
            self.rm_empty_folders(rmlist)
        
    def prnt(self, msg):
       if self.queue:
           self.queue.put(msg)
       elif self.gui:
           self.data['msg'].append(msg)
       else:
           print(msg)
    
    def rm_empty_folders(self, rmlist):
        # remove empty folders
 #       self.prnt("removing empty folders %s\n"%rmlist)
        #map(os.rmdir, iter(rmlist))
        #map does not work for some reason!!
        for d in rmlist:
            os.rmdir(d)
        
    def callmulti_process3(self):
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
        self.prnt('Pool size is %d\n' %MAX_POOL)
        with Pool(MAX_POOL) as p:
            
            results = [p.apply_async(self.processfile, (f,), 
                                     callback=self.prnt) for f in self.flist]
            for i, r in enumerate(results):
                r.wait(1000)
#                r.get()
                self.data['file_idx'] = i
                

    def callmulti_process2(self, flist):
        MAX_POOL = cpu_count() * 2
        result = []
        files = len(flist)
        if files < MAX_POOL:
            MAX_POOL = files
        P = Pool(MAX_POOL)
        P.map(self.processfile, flist)
        P.close()
        P.join()
        
    def callmulti_process(self, flist):
        MAX_POOL = 16
        lock = Lock()
        files = len(flist)
        while len(flist):
            print ('number of files to process %d\n' %len(flist))
            if len(flist) > MAX_POOL:
                processes = MAX_POOL
            else:
                processes = len(flist)
    
            for i in range(processes):
                print ('processes %d %d file %s' %(processes, i, flist[0]))
                Process(target=self.processfile, args=(('run process %d' % i),
                                                        flist[0], lock)).start()
                flist.pop(0)
        
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
        return msg
    
    def extractOriginalDate(self):
        # open image file for reading (binary mode)
        fh = open(self.file_path, 'rb')
        
        # Return Exif tags
        tags = exifread.process_file(fh)
        # print(tags)
        try:
            dto = tags['EXIF DateTimeOriginal']
        except KeyError:
            try:
                dto = tags['Image DateTime']
            except KeyError:
#                self.prnt('Photo has no date found')
                self.new_location = self.dateless
                return
                
        # extract original date from metadata
        year = dto.__str__()[:4]
        month = dto.__str__()[5:7]
        day = dto.__str__()[8:10]
        
        self.new_location = os.path.normpath(os.path.join(self.output_f, year, 
                                               '%s-%s-%s' %(year, month, day)))
 #       self.prnt ("Photo Original Date: %s-%s-%s\n" %(year, month, day))
    
    def checkDuplicates(self):
        fhash = self.hashi()

        # extract dirname from file path
        dirname = os.path.dirname(self.file_path)
        
        #check to see if we have the file already
        if fhash in self.fhashs:
            # we have a possible file duplicate since the dto exists already
            # move to duplicates folder
            self.new_location = os.path.join(self.duplicates, dirname)
        #    print ("Photo is a duplicate\n")
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
            os.mkdir(folder)
        
    def moveFile(self):
        ymd_folder = self.new_location
        y_folder = os.path.dirname(ymd_folder)
        
        self.makedir(y_folder) 
        self.makedir(ymd_folder) 
            
        npl = os.path.join(ymd_folder, os.path.basename(self.file_path))
        
        if os.path.exists(npl):
#            self.prnt('Photo exists in new folder, skipping..')
            return
        
        os.rename(self.file_path, npl)
        
    def hashi(self):
        tf = Image.open(self.file_path)
        return hashlib.md5(tf.tobytes()).hexdigest()
     
if __name__ == '__main__':
    import sys
    args = len(sys.argv)
    redirect = False
    default_path = r'C:\Users\juju\Pictures'
    print('sys.argv ', sys.argv, 'args ', args)
    
    if '-g' in sys.argv[-1]:                          # link to gui only if requested
        print('redirecting output to gui ', sys.argv)
        redirectOut()                                # GUI must be started first as is
        redirect = True
        sys.argv.pop(-1)
        
    if len(sys.argv) > 2:
        op = OrgPics(input_f=sys.argv[1], output_f=sys.argv[2], redirect=redirect)
    elif len(sys.argv) == 2:
        op = OrgPics(input_f=sys.argv[1], redirect=redirect)
    else:
        op = OrgPics(input_f=default_path, redirect=redirect)
    if not redirect:
        op.run()
        
