import os
import exifread
import hashlib
from PIL import Image
import time
from multiprocessing import *
from socket_stream_redirect0 import redirectOut        # connect my sys.stdout to socket

class OrgPics:
    organize = True
    fhashs = []
    def __init__(self, input_f, output_f='', redirect = False, queue=None, data=None):
        self.starttime = time.time()
        self.input_f = input_f
        self.output_f = output_f
        self.redirect = redirect
        self.queue = queue
        self.data = data
        
        if output_f == '':
            self.organize = False
            self.duplicates = os.path.join(input_f, 'duplicates')
            self.new_location = self.duplicates
        else:
            self.duplicates = os.path.join(output_f, 'duplicates')
            self.dateless = os.path.join(output_f, 'dateless')
                
        if self.organize and not os.path.exists(output_f):
            # path does not exist, create a new folder
            os.mkdir(output_f)
#        self.run()
        
    def __call__(self):
        self.run()
        
    def run(self):
        rmlist = []
        file_counter = 0
        flist = []
        self.prnt('starting orgpics process\ninput folder %s\n'%self.input_f)            
        for (dirname, subshere, fileshere) in os.walk(self.input_f):
            for fname in fileshere:
                if fname[-3:] in ('jpg', 'JPG'):
                    file_counter += 1              # increment counter
                    flist.append(os.path.join(dirname, fname))
            if not os.path.getsize(dirname):
                rmlist.append(dirname)
        self.rm_empty_folders(rmlist)
        self.callmulti_process3(flist)
        self.prnt('%d files processed in %d seconds\n'%(file_counter, time.time()- self.starttime))
           
    def prnt(self, msg):
       if self.queue:
           self.queue.put(msg)
       elif self.data:
           if 'msg' in self.data:
               self.data['msg'].append(msg)
           else:
               self.data['msg'] = [msg]
       else:
           print(msg)
    
    def rm_empty_folders(self, rmlist):
        # remove empty folders
        map(os.rmdir, rmlist)
        
    def callmulti_process3(self, flist):
        MAX_POOL = cpu_count() * 2
        files = len(flist)
        if files < MAX_POOL:
            MAX_POOL = files
        self.prnt('Pool size is %d\n' %MAX_POOL)
        with Pool(MAX_POOL) as p:
            
            results = [p.apply_async(self.processfile, (f,), callback=self.prnt) for f in flist]
            for r in results:
                r.wait()

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

        if self.organize:
            # extract metadata from file
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
        
        self.new_location = os.path.join(self.output_f, '%s-%s-%s' %(year, month, day))
 #       self.prnt ("Photo Original Date: %s-%s-%s\n" %(year, month, day))
    
    def checkDuplicates(self):
        fhash = self.hashi()
        
        #check to see if we have the file already
        if fhash in self.fhashs:
            # we have a possible file duplicate since the dto exists already
            # move to duplicates folder
            self.new_location = self.duplicates
        #    print ("Photo is a duplicate\n")
            self.moveFile()
            return
        else:
            self.fhashs.append(fhash)
        
    def moveFile(self):
        folder = self.new_location
        if not os.path.exists(folder):
            # path does not exist, create a new folder
            os.mkdir(folder)
        npl = os.path.join(folder, self.fname)
        
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
    default_path = r'C:\Users\220554\orgphotos'
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
        op.run()
        
