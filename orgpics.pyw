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
    def __init__(self, input_f, output_f='', redirect = False):
        self.starttime = time.time()
        self.input_f = input_f
        self.output_f = output_f
        self.redirect = redirect
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
        self.run()
        
    def run(self):
        rmlist = []
        file_counter = 0
        flist = []
        for (dirname, subshere, fileshere) in os.walk(self.input_f):
            for fname in fileshere:
                if fname[-3:] in ('jpg', 'JPG'):
                    file_counter += 1              # increment counter
                    flist.append(os.path.join(dirname, fname))
            if not os.path.getsize(dirname):
                rmlist.append(dirname)
        self.rm_empty_folders(rmlist)
        self.callmulti_process2(flist)
        print('%d files processed in %d seconds'%(file_counter, time.time()- self.starttime))            
        
    def rm_empty_folders(self, rmlist):
        # remove empty folders
        map(os.rmdir, rmlist)
       # for folder in rmlist:
       #     print('removing empty folder %s' %folder)
       #     try:
       #         os.rmdir(folder)
       #     except:
       #         print('failed to remove folder %s'%folder)
       #         pass
        
    def callmulti_process2(self, flist):
        MAX_POOL = cpu_count() * 2
        result = []
        files = len(flist)
        if files < MAX_POOL:
            MAX_POOL = files
        P = Pool(MAX_POOL)
        P.map(self.processfile, flist)
        
    #def callmulti_process(self, flist):
    #    lock = Lock()
    #    files = len(flist)
    #    while len(flist):
    #        print ('number of files to process %d' %len(flist))
    #        if len(flist) > 10:
    #            processes = 10
    #        else:
    #            processes = len(flist)
    #
    #        for i in range(processes):
    #            print ('processes %d %d file %s' %(processes, i, flist[0]))
    #            Process(target=self.processfile, args=(('run process %d' % i),
    #                                                    flist[0], lock)).start()
    #            flist.pop(0)
        
    def processfile(self, file):
        msg = 'pid:%s, processing file:%s'
        self.file_path = file
       # if self.redirect:
       #     redirectOut()     # GUI must be started first as is
        print(msg % ( os.getpid(), self.file_path))
        self.checkDuplicates()

        if self.organize:
            # extract metadata from file
            self.extractOriginalDate()

            # move file to new location
            self.moveFile()
        
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
                print('Photo has no date found')
                self.new_location = self.dateless
                return
                
        # extract original date from metadata
        year = dto.__str__()[:4]
        month = dto.__str__()[5:7]
        day = dto.__str__()[8:10]
        
        self.new_location = os.path.join(self.output_f, '%s-%s-%s' %(year, month, day))
        print ("Photo Original Date: %s-%s-%s\n" %(year, month, day))
    
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
        npl = os.path.join(folder, os.path.basename(self.file_path))
        
        if os.path.exists(npl):
            print('Photo exists in new folder, skipping..')
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
        
