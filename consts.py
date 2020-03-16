import curses

class KeyConsts:
    EXIT = ord('x')
    RELOAD_DATABASE = ord('r')
    SELECT_LIBRARY_PATH = ord('c')
    CHANGE_READ_STATE = ord(' ')
    APPLY_EXTENSION_FILTER = ord('e')
    UP = curses.KEY_UP
    DOWN = curses.KEY_DOWN
    LEFT = curses.KEY_LEFT
    RIGHT = curses.KEY_RIGHT
    BACKSPACE = curses.KEY_BACKSPACE
    ENTER = 10
