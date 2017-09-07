import sys
from tkinter import *
from tkinter.messagebox import *
from tkinter.filedialog import *
from socket import *                         # including socket.error 
from tkinter.scrolledtext import ScrolledText
from launchmodes import PortableLauncher
import time


class OrgPhotosGUI(Frame):
    rev = '1.0'
    msg0 = 'Welcome to Photo Organizer rev %s.\nSelect your input and output folders before proceeding.\n'%rev
    msg1 = 'Need to select a folder before proceeding..\n'
    msg2 = 'proceeding with your request..\n'
    msg3 = 'Photo Organizer rev %s' %rev
    source_folder = 'NA'
    destination_folder = 'NA'
    
    def __init__(self, parent=None):
        Frame.__init__(self, parent)
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
        
    def onTimer(self):
        secsSinceEpoch = time.time()
        elapsedtime = secsSinceEpoch - self.starttime
        elapsedsec = elapsedtime % 60      # extract seconds
        elapsedminh = elapsedtime // 60
        elapsedhrs = elapsedminh  // 60    # extract hours
        elapsedmin = elapsedminh % 60      # extract minutes

        # update status Bar
        self.log_st1.config(text=time.ctime(secsSinceEpoch))
        self.log_st3.config(text='session time %d:%d:%d'%(elapsedhrs, elapsedmin, elapsedsec))
        
        self.after(1000 // 1, self.onTimer)  # run N times per second
        
    def checkdata(self):
        # check data from spawned non gui program
        try:
            message = self.conn.recv(1024)            # don't block for input
            if(message):
                self._updatetext(message)
        except error:                            # raises socket.error if not ready
            pass
#            self._updatetext('no data..\n')                     
        self.after(500, self.checkdata)              # check once per second
        
    def get_folder(self, src_dest):
        folder_path = askdirectory()
        if not folder_path: return
        self._updatetext('set entry folder path %s\n' %folder_path)
        if src_dest == 'src':
            self.source_l.insert(0,'%s'%folder_path)
            self.source_l.config(bg='green', fg='white')
        else:
            self.dest_l.insert(0,'%s'%folder_path)
            self.dest_l.config(bg='green', fg='white')
    
    def call_organize(self, dest=True):
        if dest == False:
            self.destination_folder = ''
        if not self._validate_folder(dest=dest): return
        self._updatetext(self.msg2)
        self._startSocket()
        self._updatetext('Spawn non GUI script\n')
        cmd = 'orgpics.pyw %s %s -g'%(self.source_folder, self.destination_folder)
        PortableLauncher('Organize %s %s'%(self.source_folder, self.destination_folder), cmd)()  # spawn non-GUI script 

        self._updatetext('accepting\n')
        self.conn, self.addr = self.sockobj.accept()                # wait for client to connect
        self._updatetext('accepted\n')
        self.conn.setblocking(False)                           # use nonblocking socket (False=0)

        self.checkdata()
            
    def _validate_folder(self, src=True, dest=True):
        folder_list = [('source', self.source_l), ('desinantion', self.dest_l)]
        if dest == False:
            folder_list.pop(1)
        for name, entry in folder_list:
            folder = entry.get()
            if not os.path.isdir(folder):
                self._updatetext('Please enter or select a valid %s folder name\n'%name)
                return False
            else:
                if name == 'source':
                    self.source_folder = folder
                else:
                    self.destination_folder = folder
                self._updatetext('%s folder is %s\n'%(name, folder))
        if self.source_folder == self.destination_folder:
            self._updatetext('Source and destination folders cannot be the same\n')
            return False
        return True    
        
    def _updatetext(self, msg):
        self.log_t.configure(state='normal')
        self.log_t.insert('end', msg)
        self.log_t.see('end')
        self.log_t.configure(state='disabled')
        self.update()
        
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
        source_button.pack(side=RIGHT, padx=15)
        self.source_l = Entry(source_row, relief="ridge", justify=LEFT)
        self.source_l.pack(side= LEFT, fill=X, expand=YES)
        source_row.pack(side=TOP, fill=X)

        dest_row = Frame(self)
        dest_label = Label(dest_row, text="Destination Folder:", width=20, justify=LEFT, bg='orange')
        dest_label.pack(side=LEFT, fill=X)
        dest_button = Button(dest_row, text="select",
                             bg='green', width=15, fg='white',
                             command=lambda: self.get_folder('dest'))
        dest_button.pack(side=RIGHT, padx=15)
        self.dest_l = Entry(dest_row, relief="ridge", justify=LEFT)
        self.dest_l.pack(side= LEFT, fill=X, expand=YES)
        dest_row.pack(side=TOP, fill=X)
        
        # Build Message for logging
        self.log_t = ScrolledText(self, relief="ridge", bg='white', state='disabled')
        self.log_t.pack(side=TOP, fill=BOTH, expand=Y)
        
        # Build status bar for logging
        b_frame = Frame(self, bg='red')
        self.log_st1 = Label(b_frame, relief="ridge", bg='purple', width=25, fg='white')
        self.log_st1.pack(side=LEFT)
        self.log_st2 = Label(b_frame, relief="sunken", bg='blue', width=50)
        self.log_st2.pack(side=LEFT, fill=X,expand=Y)
        self.log_st3 = Label(b_frame, relief="ridge", bg='purple', width=25, fg='white')
        self.log_st3.pack(side=LEFT)
        b_frame.pack(side=BOTTOM, fill=X)
        

if __name__ == '__main__':
    root = Tk()
    myorgphoto = OrgPhotosGUI(root)
    myorgphoto.master.title("My Org Photo")
    root.mainloop()

