import sys
from tkinter import *
from tkinter.messagebox import *
from tkinter.filedialog import *
import tkinter.ttk as ttk
import tkinter.tix as tix
from socket import *                         # including socket.error 
from tkinter.scrolledtext import ScrolledText
from launchmodes import PortableLauncher
from multiprocessing import *
from threading import *
import time, queue
from orgpics import OrgPics


class OrgPhotosGUI(Frame):
    rev = '1.0'
    msg0 = 'Welcome to Photo Organizer rev %s.\nSelect your input and output folders before proceeding.\n'%rev
    msg1 = 'Need to select a folder before proceeding..\n'
    msg2 = 'proceeding with your request..\n'
    msg3 = 'Photo Organizer rev %s' %rev
    source_folder = 'NA'
    destination_folder = 'NA'
    sockets = False
    process = False
    procs = 0
    idx = 1.0
    tag = 0
    color = 0
    pattern = -1
    p = 0
    line_number = 0
    
    def __init__(self, parent=None):
        Frame.__init__(self, parent)
        parent.bind('<F3>', self.onF3)
        
        self.pack(expand=YES, fill=BOTH)
        self.starttime = time.time()
        self.makewidgets()
        self.config(bg='cyan')
        self._updatetext(self.msg0)
        self.onTimer()
        
    def _startSocket(self):
        myport = 50008
        self._updatetext('starting socket at port number %d\n'%myport)
        self.sockobj = socket(AF_INET, SOCK_STREAM)       # GUI is server, script is client
        self.sockobj.bind(('', myport))                   # config server before client
        self.sockobj.listen(5)
        
    def getElapsedtime(self, start):
        secsSinceEpoch = time.time()
        elapsedtime = secsSinceEpoch - start
        elapsedsec = elapsedtime % 60      # extract seconds
        elapsedminh = elapsedtime // 60
        elapsedhrs = elapsedminh  // 60    # extract hours
        elapsedmin = elapsedminh % 60      # extract minutes

        timestr = 'time %d:%d:%d'%(elapsedhrs, elapsedmin, elapsedsec)

        return timestr
    def onTimer(self):
        elapsed = self.getElapsedtime(self.starttime)
        # update status Bar
        self.log_st1.config(text=time.ctime(time.time()))
        self.log_st3.config(text=elapsed)
        
        self.after(1000 // 1, self.onTimer)  # run N times per second
        
    def checkdata(self):
        # check data from spawned non gui program
        msg = 'Process not started yet'
        elapsed = self.getElapsedtime(self.pstart)
        step1_msg = 'Running %s, %s jpeg files found so far' %(elapsed, 
                                                               self.d['files']) 
        step2_msg = 'Running %s, %s files processed out of %s. Pool %s'%(elapsed, 
                      self.d['file_idx'], self.d['files'], self.d['pool_size'])
                    
        if self.d['step'] == 1:
            msg = step1_msg
            self.progbar.config(mode='indeterminate', value=self.d['file_idx'], length=100)
            
        else:
            msg = step2_msg
            if self.d['files'] >= self.d['file_idx']:
                self.progbar.config(maximum= self.d['files'], mode='determinate',
                                    value=self.d['file_idx'], length=100)
                self.meter.config(value= self.d['file_idx']/self.d['files'])
        self.log_st2.config(text=msg)
            
        try:
            if self.sockets:
                message = self.conn.recv(1024)            # don't block for input
#            elif self.q and not self.q.empty():
#                message = self.q.get()
            elif 'msg' in self.d:
                message = self.d['msg']
                if(message):
#                    print(message)
                    self._updatetext(message)
                    self.d['msg'] = []
        except:                            # raises socket.error if not ready
            self._updatetext('e')
        if self.p.is_alive():
            self.after(1000, self.checkdata)              # check once per second
#            self._updatetext('=')
        else:
            self.p.join()
            self.log_st2.config(text='Thread completed in %s. %s files processed' 
                                %(elapsed, self.d['files']))
            self._updatetext('\nThread done\n')
            
            
    def get_folder(self, src_dest):
        folder_path = askdirectory()
        if not folder_path: return
        self._updatetext('%s folder path %s\n' %(src_dest, folder_path))
        if src_dest == 'src':
            self.source_l.insert(0,'%s'%folder_path)
            self.source_l.config(bg='green', fg='white')
        else:
            self.dest_l.insert(0,'%s'%folder_path)
            self.dest_l.config(bg='green', fg='white')
    
    def call_organize(self, dest=True):
        if dest == False:
            self.destination_folder = ''
            task = "clean"
        else:
            task = 'organize'
        if not self._validate_folder(dest=dest): return
        self._updatetext(self.msg2)
        if self.sockets:
            self._startSocket()
            self._updatetext('Spawn non GUI script\n')
            cmd = 'orgpics.pyw %s %s -g'%(self.source_folder, self.destination_folder)
            PortableLauncher('%s'%task, cmd)()  # spawn non-GUI script 
    
            self._updatetext('accepting\n')
            self.conn, self.addr = self.sockobj.accept()                # wait for client to connect
            self._updatetext('accepted\n')
            self.conn.setblocking(False)                           # use nonblocking socket (False=0)
        else:
            if self.process:
               self.q = Queue()
            else:
                self.d = dict()
                self.d['caller'] = 'gui'
                self.d['file_idx'] = 0
                self.d['msg'] = []
                self.d['procs'] = self.procs
                self.d['pool_size'] = 0
                self.d['step'] = 0
                self.d['files'] = 0
#                self.q = queue.Queue()
            op = OrgPics(input_f=self.source_folder, output_f=self.destination_folder, data=self.d, gui=True)
            #op = OrgPics(input_f=self.source_folder, output_f=self.destination_folder, queue=self.q)
            self.pstart = time.time()
            if self.process:
                self.p = Process(target=op)
            else:
                self.p = Thread(target=op, name='orgpics')
            self.p.start()
        self.checkdata()
        
    def _validate_folder(self, src=True, dest=True):
        folder_list = [('source', self.source_l), ('desinantion', self.dest_l)]
        if dest == False:
            folder_list.pop(1)
        for name, entry in folder_list:
            folder = entry.get()
            if not os.path.isdir(folder) or folder == 'NA':
                if name == 'source' or folder in ['', 'NA']:
                    self._updatetext('%s is not a valid folder name\nPlease enter or select a valid %s folder name\n'%(folder,name))
                    return False
                else:
                    os.mkdir(folder)
            else:
                if name == 'source':
                    self.source_folder = folder
                else:
                    self.destination_folder = folder
                self._updatetext('%s folder is %s\n'%(name, folder))
        if self.source_folder == self.destination_folder:
            self._updatetext('Source and destination folders cannot be the same\n')
            return False
        if self.p and self.p.is_alive():
            self._updatetext('Process is already running...\n')
            return False
            
        return True    
    
    def _validate_opt1(self, p, b):
        ''' only accept a number between 1 and 99 in the procs entry field '''
        
        if p.isdigit() and int(p) > 0 and int(p) < 100:
            self.procs = int(p)
            return True
        elif p == '':
            self.procs = 0
            return True
        return False
           
    def _updatetext(self, msg):
        ''' diplay text on the log area '''
        # insert line number
        
        
        if isinstance(msg,list):  msg = ''.join(l for l in msg)  
        # retreive current location
        ln_idx = 'end'
        line, char = self.log_t.index('end').split('.')
        if int(char) != 0:
            l = int(line) + 1
            print('advance')
        else:
            l = int(line)
        if msg[-1] == '\n':
            msg = msg[:-1]
        msglist = msg.split('\n')
        self.log_t.configure(state='normal')
        for m in msglist:
            m = m + '\n'
            self.line_number += 1
            ln_idx = '%d.0'%l
            ln_idx_start = '%d.0'%(l-1)
            ln_idx_end = '%d.9'%(l-1)
            log_idx_start = '%d.11'%l
#            print(self.line_number, ln_idx, ln_idx_end, log_idx_start)
            self.log_t.insert(ln_idx,'%7d  '%self.line_number)
            self.log_t.insert(log_idx_start, m)
            self.log_t.tag_add('ln', ln_idx_start, ln_idx_end)
            self.log_t.tag_config('ln', background='gold')
#            self.log_t.tag_add('log', log_idx_start )
#            self.log_t.insert('end' '\n')
            l += 1
        self.log_t.see('end')
        self.log_t.configure(state='disabled')
        self.update()
        
    def search(self, pattern):
        ''' search for a pattern in the log area 
            Assign a new tag to 
        '''
        colors = ['yellow', 'cyan', 'green', 'orange', 'magenta', 'pink',
                   'sky blue', 'floral white', 'peach puff', 'gold', 'snow2',
                  'khaki'
                  ]
        self.idx = self.log_t.search(pattern, self.idx)
        if self.idx:
            # create a new tag if it is a new search
            if (pattern != self.pattern): 
                self.pattern = pattern
                self.color = self.tag % len(colors) # rotate colors in colors list
                self.tag += 1
            tag = 'patt%s'%self.tag
            # exctract line number and position from self.idx
            l, pos = self.idx.split('.')
            pl = len(pattern) # pattern length
            new_pos = int(pos) + pl
            self.log_t.see(self.idx)
            idx2 = '%s.%s'%(l, new_pos)
            self.log_t.tag_add(tag, self.idx, idx2)
            self.log_t.tag_config(tag, background=colors[self.color])
            self.log_st2.config(text='Found %s at index %s'%(pattern, self.idx))
            self.idx = str(idx2)
        else:
            self.log_st2.config(text='Not found %s'%pattern)
            self.idx = '1.0'
            
        
    def onEnter(self, event):
        self.search(self.srch_e.get())
        
    def onF3(self, event):
        self.search(self.srch_e.get())
        
    def makewidgets(self):
        
        # Build botton buttons first to collapse last!
        b_frame = Frame(self, bg='cyan')
        go_button = Button(b_frame, text='Organize', width=20, fg='white', bg='green',
                           command=lambda:self.call_organize())
        go_button.pack(side=LEFT)
        c_button = Button(b_frame, text='Clean Folder', width=20, fg='white', bg='green',
                           command=lambda:self.call_organize(dest=False))
        c_button.pack(side=LEFT)
        mid_label = Label(b_frame, text=self.msg3, bg='orange', font=('courier', 14))
        mid_label.pack(side=LEFT, expand=YES, fill=X)
        
        self.meter = tix.Meter(b_frame)
        self.meter.pack(side=LEFT, expand=YES, fill=X)
        
        quit_button = Button(b_frame, text='Quit', width=20, fg='white', bg='red',
                             command=root.quit)
        quit_button.pack(side=RIGHT)
        b_frame.pack(side=BOTTOM, fill=X)

        # Build folders selectors
        source_row = Frame(self)
        source_label = Label(source_row, text="Source Folder:", width=20, justify=LEFT, bg='orange')
        source_label.pack(side=LEFT, fill=X)
        source_button = Button(source_row, text="select",
                               bg='green', width=15, fg='white',
                               command=lambda: self.get_folder('src'))
        source_button.pack(side=RIGHT)
        self.source_l = Entry(source_row, relief="ridge", justify=LEFT)
        self.source_l.pack(side= LEFT, fill=X, expand=YES, padx=15)
        source_row.pack(side=TOP, fill=X)

        dest_row = Frame(self)
        dest_label = Label(dest_row, text="Destination Folder:", width=20, justify=LEFT, bg='orange')
        dest_label.pack(side=LEFT, fill=X)
        dest_button = Button(dest_row, text="select",
                             bg='green', width=15, fg='white',
                             command=lambda: self.get_folder('dest'))
        dest_button.pack(side=RIGHT)
        self.dest_l = Entry(dest_row, relief="ridge", justify=LEFT)
        self.dest_l.pack(side= LEFT, fill=X, expand=YES, padx=15)
        dest_row.pack(side=TOP, fill=X)
        
        # build option section
        opt_f = Frame(self)
        opt1_l = Label(opt_f, text="Processes # [1 - 99]", width=20, justify=LEFT,  bg="orange")
        opt1_l.pack(side=LEFT, fill=X)
        vcommand = self.register(self._validate_opt1)
        self.opt1_e = Entry(opt_f, validate='all', width=3,
                            validatecommand=(vcommand, '%P', '%s'))
        self.opt1_e.pack(side=LEFT, fill=X, padx=15)
        
        self.srch_b = Button(opt_f,  text ='go!',  bg='green', fg='white', width=15, 
                             command=lambda: self.search(self.srch_e.get()))
        self.srch_b.pack(side=RIGHT)
        
        self.srch_e = Entry(opt_f)
        self.srch_e.pack(side=RIGHT, fill=X, padx=15)
        self.srch_l = Label(opt_f, text="Search Log", justify=LEFT, bg='orange')
        self.srch_l.pack(side=RIGHT, fill=X)
        opt_f.pack(side=TOP, fill=X)
        
        # Build Message for logging
        self.log_t = ScrolledText(self, relief="ridge", bg='white', fg='blue',
                                  state='disabled', font=('courier', 8, 'normal'))
        self.log_t.pack(side=TOP, fill=BOTH, expand=Y)
        
        # Build status bar for logging
        b_frame = Frame(self, bg='red')
        self.log_st1 = Label(b_frame, relief="ridge", bg='purple', width=24, fg='white')
        self.log_st1.pack(side=LEFT)
        self.log_st2 = Label(b_frame, relief="sunken", bg='blue', width=55, fg='white')
        self.log_st2.pack(side=LEFT, fill=X,expand=Y)
        self.progbar = ttk.Progressbar(b_frame, orient='horizontal', mode='determinate')
        self.progbar.pack(side=LEFT, fill=X, expand=Y)
        self.log_st3 = Label(b_frame, relief="ridge", bg='purple', width=20, fg='white')
        self.log_st3.pack(side=LEFT)
        b_frame.pack(side=BOTTOM, fill=X)
        
        # key binding
        self.srch_e.bind('<Return>', self.onEnter)
#        self.srch_e.bind('<F3>'    , self.onF3)
        

if __name__ == '__main__':
    root = tix.Tk()
   
    myorgphoto = OrgPhotosGUI(root)
    myorgphoto.master.title("My Org Photo")
    root.mainloop()

