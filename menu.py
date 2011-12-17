#!/usr/bin/env python
import sys, Tkinter as tk, re, csv, optparse, signal, commands
from optparse import OptionParser
from functools import partial
from ConfigParser import SafeConfigParser
# Should also try to import atm.functions here ...
'''
Idea is that there are three components.
We have this file - the core logic,
the menu.cfg file - the configuration,
the functions.py file
'''

def parse_args(options):
    ''' Parse the given options and arguments using optparse'''
    parser = OptionParser()
    parser.add_option("-c", "--config", metavar="FILE", dest="config",
                        help="Default: menu.cfg", default='menu.cfg')
    parser.add_option("-f", "--functions", metavar="FILE", dest="functions", 
                        help="Default: functions.py", default='menu.functions')
    parser.add_option("-g", "--gui", dest="gui", default=False, 
                        action="store_true",help="Text mode. Default: False")                    
    (options, args) = parser.parse_args()
    return (options,args)

def parse_config(config):
    '''Build a dictionary of the menu from the given config file after having removed empty lines and comments'''
    f = open(config, 'rt')
    # Want to ignore comments and then remove all commas on the ends of lines, to ensure consistency
    lines = f.readlines()
    f.close()
    # remove comments, subsequent trailing spaces and the final comma (should be at most 1 of these)
    processed_lines = [ line.split('#')[0].rstrip('\n').rstrip(' ').rstrip(',') for line in lines ]
    # Now we let the csv module parse what's left, although I'm not sure it's doing anything very clever.   
    try:
        reader = csv.reader(processed_lines,skipinitialspace = True)
    except:
        sys.exit('Couldn\t open %s' % config)
    # Would like to convert this into a dictionary, where a key is the dictionary 
    # position defined as a tuple, and the value is a list of the options at that point.
    # eg. menu_opts[('level1','level2')] = ['list','of','options','under','level','2']
    menu_opts = {}
    
    for line in reader:
        line = tuple(line) # Lists can't be keys in dictionaries
        for i in range(len(line)):
            if line[:i] not in menu_opts: menu_opts[line[:i]] = [line[i]]
            else: 
                if line[i] not in menu_opts[line[:i]]: menu_opts[line[:i]].append(line[i])
    
    return menu_opts

def handle_sigint():
    '''Gracefully quit on receiving Ctrl + c'''
    # This doesn't seem to always work, so I've wrapped the main() call in a try / except clause
    # instead until I figure it out.
    print 'Recieved Ctrl + c - exiting ...'
    sys.exit()
 
# So I can quickly test changes in Idle - use line below:
#import menu; menu_dict = menu.parse_config('D:\Edmund\Python\Scripts\menu.cfg'); menu = menu.Menu(menu_dict)

class Menu:
    '''The menu class needs to be instantiated with a dictionary built from a menu config file.\
The dictionary has the property that each key is a tuple defining a particular menu level (eg. ('level1','level2')  )\
, with the value being the list of all the options available at that level (eg. ['level3', 'command1','command2']).'''
    def __init__(self,menu_dict):
        self.position = []  # At the base of the menu
        self.menu_dict = menu_dict # This is the config file we're using
    def get_options(self,position):
        '''Display the options returned from the previous search, if applicable, or those available at this point in the menu'''
        if hasattr(self,'search_dict'):
            return_dict = self.search_dict
            del(self.search_dict)
            return return_dict
        if tuple(position) not in self.menu_dict: return -1
        else:
            # The line below is just returning a single entry of the menu_dict, but
            # in a dictionary form for consistency
            return dict([(tuple(position),sorted(self.menu_dict[tuple(position)]))])
    def choose_option(self,position,option):
        '''Move to selected level of menu / execute chosen command'''
        if self.categorise(position,option) == -1: return -1
        if self.categorise(position,option) == 'search':
            self.search(option)
        elif self.categorise(position,option) == 'sub-menu':
            position.append(option)
            self.position = position
        else:
            # Not a search or a sub-menu implies this is a command which should be run,
            # so this will call the associated 'actual-command' lying under the command entry
            # Obviously, this has yet to be implemented - it just prints the line below currently.
            self.execute_command(self.menu_dict[tuple(position + [option])][0])
        return
    def go_up(self):
        '''Move back up one level of the menu (unless already at base, in which case do nothing)'''
        if len(self.position) > 0:
            self.position.pop(len(self.position) - 1)
        return
    def search(self,regex):
        '''Returns and stores, as an object attribute, a mini-menu_dict, where regex matches \
either the key or the value or, if value is a 'command', the 'actual-command' lying underneath'''
        matches = {}
        for (key, value) in self.menu_dict.items():
            for level in key:
                if re.search(regex,level):
                    matches[key] = value
                    break
            if key not in matches:
                for entry in value:
                    if re.search(regex,entry):
                        # I'm being careful here to only add the menu entries that match
                        if key not in matches: matches[key] = [entry]
                        else: matches[key].append(entry)
                
        # Note that we may have matched the 'actual-command', as opposed to a 'sub-menu' or a 'command'
        # (which are what you see when you browse the menu).  In these cases, I only want to store the
        # command entry, not the actual command entry
        for (key,value) in matches.items():
            if self.categorise(list(key),value[0]) == 'actual-command':
                del matches[key] # we know in this case the actual-command is the only entry in value
                if tuple(list(key)[:-1]) not in matches:
                    # If key,value matches the menu position of the actual command
                    # and the actual command itself, key[:-1],[key[-1]] is the dictionary
                    # entry for the associated command you can browse to in the menu,
                    # which is what we want
                    matches[tuple(list(key)[:-1])] = [key[-1]]
        self.search_dict = matches
        # I return the dictionary here, but I think I'm more likely
        # to use the fact that I've set self.search
        return self.search_dict     
        
    def categorise(self,position,option):
        '''Returns 'sub-menu','command','actual-command' (as typed on the command line) depending on the option'''
        if tuple(position) not in self.menu_dict: return -1
        if option not in self.menu_dict[tuple(position)]: return 'search' # If someone hasn't picked a valid option, it's a search
        if tuple(position + [option]) not in self.menu_dict: return 'actual-command'
        elif tuple(position + [option]) in self.menu_dict \
        and len(self.menu_dict[tuple(position + [option])]) == 1 \
        and tuple(position + [option] + [self.menu_dict[tuple(position + [option])][0]]) not in self.menu_dict:
            return 'command'
        else: return 'sub-menu'
    
    def execute_command(self,command):
        '''Execute's the given command in the shell.  Not currently working in Git Bash, but yet to test on an actual Unix box'''
        print "Executing following command: %s" % command
        '''
        (status, output) = commands.getstatusoutput(command)
        if status:    ## Error case, print the command's output to stderr and exit
            print "Non-zero exit status - see below for output:"
            sys.stderr.write(output)
            sys.exit('Exiting')
        print "Command run successfully - output below"
        print output
        '''
        return
        
        
        
        
        
        
def run_text_menu(menu):
    while True:
        print "\n****** Menu ******"


        # Zero option is always 'go up one level' ...
        print "%d:(%s): %s\n" % (0,'Parent-menu','Go back up one level')

        # These are the current options ...
        options = menu.get_options(menu.position)
        
        # A dictionary that will keep track of what the 
        # numbered menu options actually refer to under the cover
        index_dict = {}
        
        label = 0
        # Loop through options and print them to the screen
        for index1 in range(len(options.items())):
            key,value = sorted(options.items())[index1]
            
            # Create a multi-line variable showing where you are in the menu, and print it.
            location_text = 'Root'
            for index in range(len(key)):
                if index == len(key) -1: location_text = location_text + '\n' + '--' * (index + 1) + '>' + key[index]
                else: location_text = location_text + '\n' + '--' * (index + 1) + key[index]            
            print "%s:" % location_text
            
            for index2 in range(len(value)):
                label = label + 1
                # Make a note of the menu number label -> indexes mapping
                index_dict[label] = (index1,index2)
                # Is the option a command or submenu?  Work this out so we can label it.
                category = menu.categorise(list(key),value[index2])
                if category == -1: sys.exit("Some error has occurred")
                
                print "%d:(%s):\t%s" % (label,category,value[index2])
            print "\n-------------------\n"
        
        # Take user input
        choice = raw_input('\nMake your choice: ')
        
        # Process user input
        if choice == '0': menu.go_up()
        elif re.search(r'(quit|exit)',choice): sys.exit()
        elif re.search(r'^$',choice): pass  # Do nothing if nothing has been entered
        else:
            if re.search(r'^\d+$',choice):
                # They've picked a menu entry as opposed to a search
                # Using the index_dict, work out what position and option they've chosen
                index1,index2 = index_dict[int(choice)]
                position, entries = sorted(options.items())[index1]
                option = entries[index2]
            else: position, option = menu.position, choice
            #if menu.choose_option(menu.position,menu.specify_option(menu.position,choice)) == -1:
            if menu.choose_option(list(position),option) == -1:
                sys.exit('Some error has occurred')
    return
    
class Button:
    def __init__(self,frame,position,GUI):
        self.frame = frame
        self.colour = tk.StringVar()
        self.variable = tk.StringVar()
        self.position = position
        GUI.buttons[tuple(position)] = self
        self.type = GUI.menu.categorise(self.position[:-1],self.position[-1])
        if self.type == 'command':
            self.actual_command = GUI.menu.menu_dict[tuple(self.position)][0]
            self.default_colour = GUI.colour_scheme['command-initial']
            self.colour_when_pressed = GUI.colour_scheme['command-final']         
        else:
            self.default_colour = GUI.colour_scheme['not-selected']
            self.colour_when_pressed = GUI.colour_scheme['selected']
        self.reset()
        self.button = tk.Button(frame,bg=self.colour.get(),text=self.position[-1],relief=self.relief,command = partial(GUI.button_press,self))
        if self.type == 'command':
            # Also want to make the command_display_frame show underlying 
            # command when mouse hovers over button
            self.button.bind("<Enter>", partial(GUI.display_command,self,True))
            self.button.bind("<Leave>", partial(GUI.display_command,self,False))
    def reset(self):
        self.relief = tk.RAISED
        self.colour.set(self.default_colour)
    def press(self):
        self.relief = tk.SUNKEN
        self.colour.set(self.colour_when_pressed)
    def pack(self):
        self.button.pack(side=tk.TOP,fill=tk.X,expand=tk.YES,anchor=tk.N)

                
class GUI2:
    ''' The top line of the GUI will be an inert button labelled 'search' (purely used as a label)
    alongside a text entry box, into which the user can type a regex to pull up the appropriate menu
    buttons as opposed to navigating the menu itself.  Underneath will a field used to display the
    actual underlying commad whenever the mouse hovers over a command button.  Under that, the actual
    menu buttons - the main tree on the left, and each time a button is pressed the buttons on the next
    branch will appear alongside it.  Button colours will indicate whether an option is leading to
    a submenu or whether it will actually execute a command.'''
    def __init__(self, master, menu):
        self.menu = menu
        self.master = master
        self.colour_scheme = dict([
        ('not-selected','white'),
        ('selected','grey'),
        ('command-initial','yellow'),
        ('command-final','red'),
        ('menu-title','white'),
        ('bad-regex','yellow'),
        ])
        self.buttons = {}        # key is the position as a tuple
        self.button_frames = {}  # key is the position as a tuple
        # There will be three frames - one for the 'search' label and input box,
        # one to display the underlying actual-command whenever the mouse hovers
        # over a command button and one for all the buttons.
        self.search_frame = tk.Frame(self.master)
        self.search_frame.pack(side=tk.TOP,fill=tk.X,expand=tk.YES,anchor=tk.N)
        self.command_display_frame = tk.Frame(self.master)
        self.command_display_frame.pack(side=tk.TOP,fill=tk.X,expand=tk.YES,anchor=tk.N)
        self.command_display_contents = tk.StringVar()
        self.command_display_button = tk.Entry(self.command_display_frame,textvariable = self.command_display_contents,width=len(self.command_display_contents.get()),state=tk.DISABLED,)
        self.command_display_button.pack(side=tk.TOP,fill=tk.X,expand=tk.YES,anchor=tk.N)
        self.button_frame = tk.Frame(self.master)
        self.button_frame.pack(side=tk.TOP,fill=tk.BOTH,expand=tk.YES)
        # Putting the 'search label' and input box into the search frame
        self.search_label = object()
        self.search_label.button = tk.Button(self.search_frame,text='Search',state=tk.DISABLED,disabledforeground='black')
        self.search_label.button.pack(side=tk.LEFT,fill=tk.BOTH,anchor=tk.N)
        self.search_entry = object()
        self.search_entry.input = tk.StringVar()  # Variable to keep the contents of the search
        self.search_entry.colour = tk.StringVar()
        self.search_entry.colour.set(self.colour_scheme['not-selected'])
        self.search_entry.button = tk.Entry(self.search_frame,textvariable=self.search_entry.input,bg=self.search_entry.colour.get(),state=tk.NORMAL,)
        self.search_entry.button.focus_set()
        # The binding on the line below triggers the search event on each key press
        self.search_entry.button.bind("<KeyRelease>", self.search)     
        self.search_entry.button.pack(side=tk.LEFT,fill=tk.BOTH,expand=tk.YES,anchor=tk.N)

        # Display buttons for current position
        self.display_buttons([])

    def display_command(self,button,true_or_false,event):
        ''' when the mouse hovers over a command, this function displays the actual command underneath
        in the command_display_buttons'''
        if true_or_false == True:
            self.command_display_contents.set(button.actual_command)
        else:
            self.command_display_contents.set('')
        # Don't seem to need to call 'configure' to get this to update
        # A property of bindings, perhaps?
        return
        
        
    def display_buttons(self,position):
        # We're supposing here someone has just clicked a button, as opposed to doing a search.
        # Position is a list defining the current position for which we want to display buttons.
        # Think I will have to use a different function to display the results of a search.
        # eg. ['level1','level2','level3']
        # First thing is to remove unwanted button frames and their associated buttons
        frames = self.button_frames.keys()[:]
        # unless position = [] (ie. someone has just cleared a search), we never want to clear the base frame
        if position != []: frames.remove(())
        for frame in frames:
            if frame != tuple(position[:len(frame)]) or frame == ():
                # Above if statement means we are talking about a frame we don't want displayed any more
                # First, remove the stored references to all its buttons
                for button in self.buttons.keys()[:]:
                    if self.buttons[button].frame == self.button_frames[frame]:
                        del(self.buttons[button])
                # Now stop displaying the frame (and thus all it's buttons) and the reference to that
                self.button_frames[frame].pack_forget()
                #self.button_frames[frame].destroy()   # don't think I need this
                del(self.button_frames[frame])
        
        # Now we create all the frames and buttons we need, starting with the base frame
        # This would only ever be deleted when someone performs a search as opposed to clicking through the menu
        # (the following looks complicated - it's just that get_options returns a dict, and '()' is the key
        # for the root of the menu
        # this is probably a mistake - it was me trying to be consistent, but things would look much
        # simpler if it just returned a list of the options rather than a dictionary with a single entry!)
        if () not in self.button_frames:
            self.button_frames[()] = tk.Frame(self.button_frame)
            self.button_frames[()].pack(side=tk.LEFT,anchor=tk.N)
            print "self.menu.get_options([])[()] is %s" % self.menu.get_options([])[()]
            for option in self.menu.get_options([])[()]:
                button = Button(self.button_frames[()],[option],self)
                button.pack()
            
        
        # Now I build up the menu from left to right, one level at a time,
        # until I've displayed the level required.
        # If the button that has this position is an actual command, we don't want to 
        # create a frame for it, as that would only contain the underlying 'actual-command'
        # (the 'actual command' isn't supposed to be a button - 
        # it's a command that's executed by clicking the parent 'command' button).
        length = len(position)
        for button in self.buttons.values():
            if button.position == position and button.type == 'command': length = length - 1
        for i in range(length):
            
            # A new frame for the next lot of buttons if it doesn't already exist
            temp_position = position[:i+1]
            if tuple(temp_position) not in self.button_frames:
                # We need to create the frame and populate it with buttons
                self.button_frames[tuple(temp_position)] = tk.Frame(self.button_frame)
                self.button_frames[tuple(temp_position)].pack(side=tk.LEFT,anchor=tk.N)
                for option in self.menu.get_options(temp_position)[tuple(temp_position)]:
                    frame = self.button_frames[tuple(temp_position)]
                    button = Button(frame,temp_position + [option],self)  # This also puts an entry in self.buttons
                    button.pack()
        
        # Colour and set the relief of all the buttons.
        for button in self.buttons.values():
            button.button.configure(bg=button.colour.get(),relief=button.relief)

        return
    
    def search(self,event):
        # I don't want this function doing a search unless a regular ASCII 
        # character is pressed (or backspace)
        # We also don't want it doing a search unless we have a legitimate regex
        # Idea is to turn the search box yellow whilst expression isn't valid
        colour_var = self.search_entry.colour
        if self.search_entry.input.get() == '':
            # Just display standard root menu if there is no regex:
            self.menu.position = []
            self.display_buttons(self.menu.position)
        else:
            if event.char != '' or event.keysym == 'BackSpace':
                try:
                    options_dict = self.menu.search(self.search_entry.input.get())
                except:
                    # Likely user has entered a partially complete regex
                    # Let's turn the colour yellow to let them know
                    colour_var.set(self.colour_scheme['bad-regex'])
                    self.search_entry.button.configure(bg=colour_var.get())
                    options_dict = {}  # probably want some kind of loop that keeps trying until it gets a substring that is a legitimate search
                else:
                    # Search ran ok - string must be a valid regex
                    # Make sure colour of text box reflects that
                    colour_var.set(self.colour_scheme['not-selected'])
                    self.search_entry.button.configure(bg=colour_var.get())
                # I need to add code to display the contents of the options_dict
                print len(options_dict.items())
                print '\n\n'
                if len(options_dict.items()) > 0:
                    for key, value in options_dict.items(): print key, value
        return

    def button_press(self,button):
        self.menu.position = button.position
        
        # If button is a primed command, execute the command
        already_pressed = False
        if button.type == 'command' and button.colour.get() == button.colour_when_pressed:
            self.menu.execute_command(button.actual_command)
            already_pressed = True
            
        # Reset appearance of all buttons except the current one
        for other_button in self.buttons.values(): 
            other_button.reset()
        
        # Now ensure the correct buttons appear pressed
        # The complication is that when you press a primed command, the command is executed and
        # the button is then effectively un-pressed, so in this case I don't want to press it again
        for other_button in self.buttons.values():
            if tuple(other_button.position) == tuple(button.position[:len(other_button.position)]):
                if other_button.position == button.position:
                    if already_pressed == False:
                        other_button.press()
                else: other_button.press()

        self.display_buttons(self.menu.position)
        return
        
class object:
    def __init__(self):
        pass
                
class GUI:
    def __init__(self, master, menu):
        # I want a search box and the results of a get_options call
        self.info = {}  # Not sure what will be put in this dict yet!
        self.info['menu'] = menu  # Actually, I can usefully store the menu object in there
        self.info['colour-scheme'] = dict([
        ('not-selected','white'),
        ('selected','green'),
        ('command-initial','yellow'),
        ('command-final','red'),
        ('menu-title','white'),
        ('bad-regex','yellow'),
        ])
        self.info['levels'] = {}
        # Now make the search button.  This will always be on the screen, at the top.
        self.info['search'] = {}
        search = self.info['search']
        search['frame'] = tk.Frame(master)
        search['frame'].pack(side=tk.TOP,fill=tk.X,expand=tk.YES,anchor=tk.N)
        # We want a search label ...
        search['label'] = tk.Button(search['frame'],text='Search',state=tk.DISABLED,disabledforeground='black')
        search['label'].pack(side=tk.LEFT,fill=tk.BOTH,anchor=tk.N)
        # And an Entry button for the search text
        search['var'] = tk.StringVar()  # Variable to keep the contents of the search
        search['colour'] = tk.StringVar()
        search['colour'].set('white')
        search['button'] = tk.Entry(search['frame'],textvariable=search['var'],bg=search['colour'].get(),state=tk.NORMAL,)
        search['button'].focus_set()
        # The binding on the line below triggers the search event on each key press
        search['button'].bind("<KeyRelease>", self.search)     
        search['button'].pack(side=tk.LEFT,fill=tk.BOTH,expand=tk.YES,anchor=tk.N)

        # The other menu buttons go in the frame below the search box
        self.info['buttons'] = tk.Frame(master)
        self.info['buttons'].pack(side=tk.TOP,fill=tk.BOTH,expand=tk.YES)
        
        # Display buttons for current position
        self.display_buttons([])
    
    #def display_menu(self, 
        
    def search(self,event):
        # I don't want this function doing a search unless a regular ASCII 
        # character is pressed (or backspace)
        # We also don't want it doing a search unless we have a legitimate regex
        # Idea is to turn the search box yellow whilst expression isn't valid
        colour_var = self.info['search']['colour']
        if event.char != '' or event.keysym == 'BackSpace':
            #print "Current text is %s" % self.info['search']['var'].get()
            try:
                options_dict = self.info['menu'].search(self.info['search']['var'].get())
            except:
                # Likely user has entered a partially complete regex
                # Let's turn the colour yellow to let them know
                colour_var.set(self.info['colour-scheme']['bad-regex'])
                self.info['search']['button'].configure(bg=colour_var.get())
            else:
                # Search ran ok - string must be a valid regex
                # Let's ensure the colour is white
                colour_var.set('white')
                self.info['search']['button'].configure(bg=colour_var.get())
            # I need to add code to display the contents of the options_dict
            print len(options_dict.items())
            print '\n\n'
            if len(options_dict.items()) > 0:
                for key, value in options_dict.items(): print key, value
        return
    
    def display_buttons(self,position):
        # Position is a list defining the current position. eg.
        # ['level1','level2','level3']
        menu = self.info['menu']
        # levels is a dictionary which holds all the information
        # about what's actually being displayed
        levels = self.info['levels']

        for index in range(len(position)+1):
            # Are we currently displaying this level of the menu?
            # If not, destroy the equivalent level we are displaying
            # and all sublevels
            if tuple(position[:index]) not in levels:
                # remove all entries of levels that have length index and above.
                for entry in levels.keys():
                    if len(entry) >= index:
                        # Stop displaying the level
                        levels[entry]['frame'].pack_forget()
                        levels[entry]['frame'].destroy()
                        # remove the reference
                        del levels[entry]
                # Add in new entry to levels
                levels[tuple(position[:index])] = {}
                current_level = levels[tuple(position[:index])]
                current_level['frame'] = tk.Frame(self.info['buttons'])
                current_level['frame'].pack(side=tk.LEFT,anchor=tk.N)
                # get the options
                options_dict=menu.get_options(position[:index])
                current_level['buttons'] = {}
                print options_dict.values()
                #options_dict.values() should be a list of lists, but we only expect one list
                for option in options_dict.values()[0]:
                    current_level['buttons'][tuple(option)] = {}
                    button = current_level['buttons'][tuple(option)]
                    button['position'] = position[:index] + [option]
                    button['colour'] = tk.StringVar()
                    # I want the colour to be red if the button's a command
                    if menu.categorise(position[:index],option) == 'command':
                        button['colour'].set('yellow')
                    else: button['colour'].set('white')
                    button['button'] = tk.Button(current_level['frame'],bg=button['colour'].get(),text=option,command = partial(self.menu_select,button))
                    button['button'].pack(side=tk.TOP,fill=tk.X,expand=tk.YES,anchor=tk.N)
        return
                    
    def menu_select(self,button):
        # Menu button has been pressed
        # Reset the colour of all grey coloured buttons
        levels = self.info['levels']
        for level in levels.keys():
            for entry in levels[level]['buttons']:
                colour_var = levels[level]['buttons'][entry]['colour']
                if colour_var.get() == 'grey':
                    colour_var.set('not-selected')
                    levels[level]['buttons'][entry]['button'].configure(bg=colour_var.get())
        # Set the colour of all relevant sub-buttons to 'selected'
        '''
        position = button['position']
        for index in range(len(position)+1):
            pos = position[:index]
            button = position[index]
            if tuple(pos) in levels:
                colour_var = levels[tuple(pos)]['buttons'][button]['colour']
                colour_var.set('grey')
                levels[tuple(pos)]['buttons'][button]['button'].configure(bg=colour_var.get())
        '''
        
        
        #button['colour'].set('grey')
        #button['button'].configure(bg=button['colour'].get())
        # Display sub-menu
        # Just got to work out the position of the button that's been pressed
        self.display_buttons(button['position'])
        return
        
    
def run_gui_menu(menu):
    root = tk.Tk()
    root.title('Menu')
    GUI2(root,menu)
    root.mainloop()
    return

def main(): 
    
    # Parse input options
    options, args = parse_args(sys.argv[0:])
    
    # Read in menu config file
    menu_dict = parse_config(options.config)

    
    # Make an instance of the menu class
    menu = Menu(menu_dict)
    
    # Run the menu GUI if user so wishes ...
    if options.gui == True: run_gui_menu(menu)
    
    # ... else run the text based menu.
    if options.gui == False: run_text_menu(menu)
    
    return

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit('Quitting')