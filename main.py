#!/bin/env python3

import sys
import curses, curses.panel, curses.ascii
import os, os.path
import sqlite3
import hashlib
from functools import reduce

def draw(stdscr):
    characterPressed = 0
    items = []
    position = 0
    startListPosition = 0
    endListPosition = 0
    readItems = 0
    libraryPath = ""
    libraryPathTemp = ""
    changeLibraryPathMode = False

    # Clear and refresh the screen for a blank canvas
    stdscr.clear()
    stdscr.refresh()
    curses.curs_set(0)

    # Start colors in curses
    curses.start_color()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_WHITE)

    windows, panels = createPanels()

    while characterPressed != ord('x'):
        height, width = stdscr.getmaxyx()

        if characterPressed == 10:
            changeLibraryPathMode = False
            libraryPath = libraryPathTemp
            panels[0].hide()
            # TODO Check which flag is switched on

        if changeLibraryPathMode:
            if characterPressed == curses.KEY_BACKSPACE:
                libraryPathTemp = libraryPathTemp[:-1]
            else:
                libraryPathTemp += chr(characterPressed)

            windows[0].attron(curses.color_pair(2))
            windows[0].addstr(1, 1, "Path to library: " + libraryPathTemp.ljust(int(width - 0.5 * width - 19), " "))
            windows[0].attroff(curses.color_pair(2))
        else:
            if (characterPressed == curses.KEY_DOWN) and (len(items) != 0):
                position = ((position + 1) % len(items))
                if position > endListPosition:
                    startListPosition = startListPosition + 1
                    endListPosition = endListPosition + 1
                if position < startListPosition:
                    startListPosition = position
                    endListPosition = position
            elif (characterPressed == curses.KEY_UP) and (len(items) != 0):
                position = ((position - 1) % len(items))
                if position < startListPosition:
                    startListPosition = startListPosition - 1
                    endListPosition = endListPosition - 1
                if position > endListPosition:
                    startListPosition = position
                    endListPosition = position
            elif (characterPressed == curses.KEY_RIGHT) and (len(items) != 0):
                delta = endListPosition - startListPosition
                if (endListPosition + delta) > len(items):
                    endListPosition = len(items) - 1
                    startListPosition = endListPosition - delta
                    position = endListPosition
                else:
                    startListPosition = startListPosition + delta
                    endListPosition = endListPosition + delta
                    position = startListPosition
            elif (characterPressed == curses.KEY_LEFT) and (len(items) != 0):
                delta = endListPosition - startListPosition
                if (startListPosition - delta) < 0:
                    startListPosition = 0
                    endListPosition = startListPosition + delta
                else:
                    startListPosition = startListPosition - delta
                    endListPosition = endListPosition - delta
                position = startListPosition
            elif characterPressed == ord('r'):
                if os.path.isdir(libraryPath):
                    window = curses.newwin(7, 24, int(height - 0.5 * height - 4), int(width / 2 - 12))
                    window.erase()
                    window.attron(curses.color_pair(2))
                    window.box()
                    window.addstr(1, 1, "".ljust(22, " "))
                    window.addstr(2, 1, "".ljust(22, " "))
                    window.addstr(3, 1, "     Reloading...     ")
                    window.addstr(4, 1, "".ljust(22, " "))
                    window.addstr(5, 1, "".ljust(22, " "))
                    window.attroff(curses.color_pair(2))
                    windows[1] = window
                    panels[1].replace(window)
                    panels[1].top()
                    panels[1].show()
                    curses.panel.update_panels()
                    stdscr.refresh()
                    
                    if libraryPath[len(libraryPath) - 1] != "/":
                        libraryPath = libraryPath + "/"

                    if not checkIfDatabaseExists(libraryPath):
                        createDatabase(libraryPath)

                    databaseItems = getItemsFromDatabase(libraryPath)
                    filePaths = listFiles(libraryPath)
                    fileHashes = calculateHashes(libraryPath, filePaths)
                    items = {} # {"filePath": [False, False]} - first one if it exists in filePaths, second if in database
                    insertStatements = []
                    deleteStatements = []

                    for filePath in filePaths:
                        items[filePath] = [True, False]

                    for databaseItem in databaseItems:
                        data = items.get(databaseItem[1], [False, True])
                        data[1] = True
                        items[databaseItem[1]] = data

                    for filePath, info in items.items():
                        if info[0] and not info[1]:
                            insertStatements += [["INSERT INTO documents (relative_path, content_hash, is_read) VALUES (?, ?, 0)", filePath, fileHashes[filePath]]]

                        if not info[0] and info[1]:
                            deleteStatements += [["DELETE FROM documents WHERE relative_path=?", filePath]]
                            
                    
                    insertData(libraryPath, insertStatements)
                    deleteData(libraryPath, deleteStatements)

                    items = getItemsFromDatabase(libraryPath)
                    readItems = reduce((lambda a, b: a + b), list(map(lambda x: x[3], items)))
                    panels[1].hide()
                    curses.panel.update_panels()
            elif characterPressed == ord('c'):
                changeLibraryPathMode = True
                window = curses.newwin(3, int(width - 0.5 * width), int(height - 0.5 * height - 2), int(width - 0.75 * width))
                window.erase()
                window.attron(curses.color_pair(2))
                window.box()
                window.addstr(1, 1, "Path to library: " + libraryPath.ljust(int(width - 0.5 * width - 19), " "))
                window.attroff(curses.color_pair(2))
                windows[0] = window
                panels[0].replace(window)
                panels[0].top()
                panels[0].show()
                curses.panel.update_panels()
                libraryPathTemp = libraryPath
            elif characterPressed == ord(' '):
                if len(items) > 0:
                    items[position] = (items[position][0], items[position][1], items[position][2], int(not items[position][3]))
                    updateDocument(libraryPath, items[position])
                    readItems = reduce((lambda a, b: a + b), list(map(lambda x: x[3], items)))

        if len(items) > 0:
            if (height - 2) != (endListPosition - startListPosition):
                endListPosition = (startListPosition + (height - 3))
                if position > endListPosition:
                    endListPosition = position
                    startListPosition = endListPosition - (height - 3)
            if endListPosition >= len(items):
                endListPosition = len(items) - 1
                startListPosition = endListPosition - (height - 3)

        stdscr.clear()

        if changeLibraryPathMode:
            windows[0].attron(curses.color_pair(3))
            windows[0].addstr(1, 1 + 17 + len(libraryPathTemp), " ")
            windows[0].attroff(curses.color_pair(3))

        # Items list
        itemsListHeader = " Number | Is read? | Path"
        stdscr.attron(curses.color_pair(1))
        stdscr.addstr(0, 0, itemsListHeader)
        stdscr.addstr(0, len(itemsListHeader), " " * (width - len(itemsListHeader) - 1))
        stdscr.attroff(curses.color_pair(1))
        if len(items) > 0:
            drawItems(stdscr, items[startListPosition:(endListPosition + 1)], items[position], startListPosition)

        # Status bar
        statusbarstr = " e(x)it | (c)hange library path | (r)eload | (SPC) read/unread | Read items: {}/{}".format(readItems, len(items))
        stdscr.attron(curses.color_pair(1))
        stdscr.addstr(height - 1, 0, statusbarstr)
        stdscr.addstr(height - 1, len(statusbarstr), ("library: " + libraryPath + " ").rjust((width - len(statusbarstr) - 1), " "))
        stdscr.attroff(curses.color_pair(1))

        curses.panel.update_panels()

        # Refresh the screen
        stdscr.refresh()
        # Wait for next input
        characterPressed = stdscr.getch()

def main():
    curses.wrapper(draw)

def createPanels():
    windows = []
    panels = []

    windows.append(curses.newwin(0, 0, 0, 0)) # DB path
    panels.append(curses.panel.new_panel(windows[0]))

    windows.append(curses.newwin(0, 0, 0, 0)) # Info about refreshing (also if give path is not directory)
    panels.append(curses.panel.new_panel(windows[1]))

    windows.append(curses.newwin(0, 0, 0, 0)) # Saving extensions
    panels.append(curses.panel.new_panel(windows[2]))

    windows.append(curses.newwin(0, 0, 0, 0)) # Info after reloading DB
    panels.append(curses.panel.new_panel(windows[3]))

    panels[0].hide()
    panels[1].hide()
    panels[2].hide()
    panels[3].hide()

    return windows, panels

def listFiles(directory):
    filesList = []
    includedExtensions = [".pdf", ".doc", ".docx", ".odt", ".mobi", ".epub", ".djvu", ".jpg", ".jpeg", ".png"]

    if os.path.isdir(directory):
        for path, subdirs, files in os.walk(directory):
            for name in files:
                add = False

                if name == "database.db":
                    continue

                #for extension in includedExtensions:
                #    if name.lower().endswith(extension):
                #        add = True
                #        break
                add = True

                if add:
                    filesList += [os.path.join(path, name).replace(directory, "")]

    return filesList

def calculateHashes(directory, fileList):
    BUFFER_SIZE = 10 * 2**20
    hashes = dict()
    for filePath in fileList:
        with open(directory + filePath, 'rb') as file:
            hash = hashlib.sha1()
            while True:
                data = file.read(BUFFER_SIZE) #10MB
                if not data:
                    break
                hash.update(data)
            hashes[filePath] = hash.hexdigest()

    return hashes

def createDatabase(directory):
    result = False

    try:
        connection = sqlite3.connect(directory + "database.db")
        connection.cursor().execute("CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY, relative_path text NOT NULL UNIQUE, content_hash text NOT NULL, is_read INTEGER NOT NULL)")
        result = True
    except Exception:
        pass
    finally:
        connection.close()

    return result

def checkIfDatabaseExists(directory):
    return os.path.isfile(directory + "database.db")

def getItemsFromDatabase(directory):
    results = []

    try:
        connection = sqlite3.connect(directory + "database.db")
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM documents ORDER BY relative_path ASC")
        results = cursor.fetchall()
    except Exception:
        pass
    finally:
        connection.close()

    return results

def insertData(directory, insertStatements):
    result = False

    try:
        connection = sqlite3.connect(directory + "database.db")
        for statement in insertStatements:
            connection.cursor().execute(statement[0], [statement[1], statement[2]])
        connection.commit()
        result = True
    except Exception:
        pass
    finally:
        connection.close()

    return result

def deleteData(directory, deleteStatements):
    result = False

    try:
        connection = sqlite3.connect(directory + "database.db")
        for statement in deleteStatements:
            connection.cursor().execute(statement[0], [statement[1]])
        connection.commit()
        result = True
    except Exception:
        pass
    finally:
        connection.close()

    return result

def drawItems(screen, items, selectedItem, startPosition):
    index = 1
    for item in items:
        if item == selectedItem:
            screen.attron(curses.color_pair(1))
        screen.addstr(index, 0, "{:^8}|{:^10}| {}".format(startPosition + index, ("*" if item[3] == 1 else ""), item[1]))
        if item == selectedItem:
            screen.attroff(curses.color_pair(1))
        index = index + 1

def updateDocument(directory, document):
    result = False

    try:
        connection = sqlite3.connect(directory + "database.db")
        connection.cursor().execute("UPDATE documents SET is_read = ? WHERE id = ?", [document[3], document[0]])
        connection.commit()
        result = True
    except Exception:
        pass
    finally:
        connection.close()

    return result

if __name__ == "__main__":
    main()

#TODO REFACTOR CODE
#TODO HANDLE BETTER SCREEN SIZES
#TODO ADD POSSIBILITY FOR USER TO CHANGE FILES EXTENSION FILTER
#TODO ADD HASH OF FILE BASED ON CONTENT TO CHANGE ONLY FILE NAME IN CASE
#TODO ADD INFO WINDOW ABOUT ADDED/MOVED/REMOVED FILES
#TODO ADD HANDLER FOR SITUATION WHERE THERE IS NO ITEMS IN DIRECTORY
