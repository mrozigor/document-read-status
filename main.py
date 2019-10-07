#!/bin/env python3

import sys
import curses, curses.panel, curses.ascii
import os, os.path
import sqlite3
import hashlib
from functools import reduce

class View:
    STATUS_BAR = " e(x)it | (c)hange library path | (r)eload | (SPC) read/unread | Read items: {}/{}"
    ITEMS_LIST_HEADER = " Number | Is read? | Path"

    def __init__(self, screen):
        self.screen = screen
        self.initializeCurses()
        self.createPanels()

    def initializeCurses(self):
        self.screen.clear()
        self.screen.refresh()
        curses.curs_set(0)

        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_WHITE)

    def createPanels(self):
        self.windows = []
        self.panels = []

        self.windows.append(curses.newwin(0, 0, 0, 0)) # DB path
        self.panels.append(curses.panel.new_panel(self.windows[0]))

        self.windows.append(curses.newwin(0, 0, 0, 0)) # Info about refreshing (also if given path is not directory)
        self.panels.append(curses.panel.new_panel(self.windows[1]))

        self.windows.append(curses.newwin(0, 0, 0, 0)) # Info after reloading DB
        self.panels.append(curses.panel.new_panel(self.windows[2]))

        self.windows.append(curses.newwin(0, 0, 0, 0)) # Extensions window
        self.panels.append(curses.panel.new_panel(self.windows[3]))

        self.panels[0].hide()
        self.panels[1].hide()
        self.panels[2].hide()
        self.panels[3].hide()

    def getPressedCharacter(self):
        return self.screen.getch()

    def drawScreen(self, items, startListPosition, endListPosition, position, readItems, libraryPath):
        self.height, self.width = self.screen.getmaxyx()
        # Items list
        self.screen.attron(curses.color_pair(1))
        self.screen.addstr(0, 0, self.ITEMS_LIST_HEADER)
        self.screen.addstr(0, len(self.ITEMS_LIST_HEADER), " " * (self.width - len(self.ITEMS_LIST_HEADER) - 1))
        self.screen.attroff(curses.color_pair(1))
        if len(items) > 0:
            drawItems(self.screen, items[startListPosition:(endListPosition + 1)], items[position], startListPosition)

        # Status bar
        statusBar = self.STATUS_BAR.format(readItems, len(items))
        self.screen.attron(curses.color_pair(1))
        self.screen.addstr(self.height - 1, 0, statusBar)
        self.screen.addstr(self.height - 1, len(statusBar), ("library: " + libraryPath + " ").rjust((self.width - len(statusBar) - 1), " "))
        self.screen.attroff(curses.color_pair(1))

        curses.panel.update_panels()
        self.screen.refresh()

    def showLibrarySelectionDialog(self, currentLibraryPath):
        window = curses.newwin(3, int(self.width - 0.5 * self.width), int(self.height - 0.5 * self.height - 2), int(self.width - 0.75 * self.width))
        window.attron(curses.color_pair(2))
        window.box()
        window.attroff(curses.color_pair(2))
        self.windows[0] = window
        self.panels[0].replace(window)
        self.panels[0].top()
        self.panels[0].show()

        characterPressed = -1

        while characterPressed != 10:
            if characterPressed == curses.KEY_BACKSPACE:
                currentLibraryPath = currentLibraryPath[:-1]
            else:
                try:
                    currentLibraryPath += chr(characterPressed)
                except ValueError:
                    pass

            self.windows[0].attron(curses.color_pair(2))
            self.windows[0].addstr(1, 1, "Path to library: " + currentLibraryPath.ljust(int(self.width - 0.5 * self.width - 19), " "))
            self.windows[0].attroff(curses.color_pair(2))
            curses.panel.update_panels() # TODO IS THIS REALLY NECESSARY?
            self.screen.refresh()

            characterPressed = self.getPressedCharacter()

        self.panels[0].hide()
        curses.panel.update_panels()
        self.screen.refresh()

        return currentLibraryPath

def main(screen):
    view = View(screen)
    characterPressed = 0
    items = []
    position = 0
    startListPosition = 0
    endListPosition = 0
    readItems = 0
    libraryPath = ""
    infoWindowMode = False

    while characterPressed != ord('x'):
        if infoWindowMode:
            if characterPressed == 10:
                infoWindowMode = False
                panels[2].hide()
            else:
                characterPressed = screen.getch()
                # TODO Fix this
                continue

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
                    screen.refresh()
                    
                    if libraryPath[len(libraryPath) - 1] != "/":
                        libraryPath = libraryPath + "/"

                    if not checkIfDatabaseExists(libraryPath):
                        createDatabase(libraryPath)

                    databaseItems = getItemsFromDatabase(libraryPath)
                    filePaths = listFiles(libraryPath)
                    fileHashes, duplicatedFiles = calculateHashes(libraryPath, filePaths)
                    databaseHashes = {}
                    items = {} # {"fileHash": [False, False]} - first one if it exists in fileHashes, second if in database
                    insertStatements = []
                    deleteStatements = []
                    updateStatements = []

                    for fileHash, filePath in fileHashes.items():
                        items[fileHash] = [True, False]

                    for databaseItem in databaseItems:
                        data = items.get(databaseItem[2], [False, True])
                        data[1] = True
                        items[databaseItem[2]] = data
                        databaseHashes[databaseItem[2]] = databaseItem[1]

                    addedItems = 0
                    removedItems = 0
                    movedItems = 0
                    
                    for fileHash, info in items.items():
                        if info[0] and not info[1]:
                            insertStatements += [["INSERT INTO documents (relative_path, content_hash, is_read) VALUES (?, ?, 0)", fileHashes[fileHash], fileHash]]
                            addedItems += 1

                        if not info[0] and info[1]:
                            deleteStatements += [["DELETE FROM documents WHERE content_hash=?", fileHash]]
                            removedItems += 1

                        if info[0] and info[1]:
                            if fileHashes[fileHash] != databaseHashes[fileHash]:
                                updateStatements += [["UPDATE documents SET relative_path=? WHERE content_hash=?", fileHashes[fileHash], fileHash]]
                                movedItems += 1
                            
                    
                    insertData(libraryPath, insertStatements)
                    deleteData(libraryPath, deleteStatements)
                    updateData(libraryPath, updateStatements)

                    items = getItemsFromDatabase(libraryPath)
                    readItems = reduce((lambda a, b: a + b), list(map(lambda x: x[3], items)))
                    panels[1].hide()
                    window = curses.newwin(9, 20, int(height - 0.5 * height - 5), int(width / 2 - 10))
                    window.erase()
                    window.attron(curses.color_pair(2))
                    window.box()
                    window.addstr(1, 1, "".ljust(18, " "))
                    window.addstr(2, 1, "       INFO       ")
                    window.addstr(3, 1, "".ljust(18, " "))
                    window.addstr(4, 1, (" " + str(addedItems) + " files added").ljust(18, " "))
                    window.addstr(5, 1, (" " + str(removedItems) + " files removed").ljust(18, " "))
                    window.addstr(6, 1, (" " + str(movedItems) + " files moved").ljust(18, " "))
                    window.addstr(7, 1, "".ljust(18, " "))
                    window.attroff(curses.color_pair(2))
                    windows[2] = window
                    panels[2].replace(window)
                    panels[2].top()
                    panels[2].show()
                    curses.panel.update_panels()
                    infoWindowMode = True
            elif characterPressed == ord('c'):
                libraryPath = view.showLibrarySelectionDialog(libraryPath)
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

        screen.clear()

        view.drawScreen(items, startListPosition, endListPosition, position, readItems, libraryPath)

        # Wait for next input
        characterPressed = view.getPressedCharacter()

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
    duplicatedFiles = [] # TODO MAKE LIST OF DUPLICATES AND SHOW IT
    for filePath in fileList:
        with open(directory + filePath, 'rb') as file:
            hash = hashlib.sha1()
            while True:
                data = file.read(BUFFER_SIZE) #10MB
                if not data:
                    break
                hash.update(data)
            hashes[hash.hexdigest()] = filePath

    return hashes, duplicatedFiles

def createDatabase(directory):
    result = False

    try:
        connection = sqlite3.connect(directory + "database.db")
        connection.cursor().execute("CREATE TABLE IF NOT EXISTS documents (content_hash text PRIMARY KEY, relative_path text NOT NULL UNIQUE, is_read INTEGER NOT NULL)")
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

def updateData(directory, updateStatements):
    result = False

    try:
        connection = sqlite3.connect(directory + "database.db")
        for statement in updateStatements:
            connection.cursor().execute(statement[0], [statement[1], statement[2]])
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
    curses.wrapper(main)

#TODO REFACTOR CODE
#TODO HANDLE BETTER SCREEN SIZES
#TODO ADD POSSIBILITY FOR USER TO CHANGE FILES EXTENSION FILTER
#TODO ADD HANDLER FOR SITUATION WHERE THERE IS NO ITEMS IN DIRECTORY
#TODO ADD HANDLING FOR TWO FILES WITH SAME CONTENT AND DIFFERENT TITLES
