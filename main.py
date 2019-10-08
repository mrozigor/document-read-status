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

    def showReloadLibraryDialog(self):
        window = curses.newwin(7, 24, int(self.height - 0.5 * self.height - 4), int(self.width / 2 - 12))
        window.attron(curses.color_pair(2))
        window.box()
        window.addstr(1, 1, "".ljust(22, " "))
        window.addstr(2, 1, "".ljust(22, " "))
        window.addstr(3, 1, "     Reloading...     ")
        window.addstr(4, 1, "".ljust(22, " "))
        window.addstr(5, 1, "".ljust(22, " "))
        window.attroff(curses.color_pair(2))
        self.windows[1] = window
        self.panels[1].replace(window)
        self.panels[1].top()
        self.panels[1].show()
        curses.panel.update_panels()
        self.screen.refresh()

    def hideReloadLibraryDialog(self):
        self.panels[1].hide()

    def showReloadSummaryDialog(self, addedItems, removedItems, movedItems):
        window = curses.newwin(9, 20, int(self.height - 0.5 * self.height - 5), int(self.width / 2 - 10))
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
        self.windows[2] = window
        self.panels[2].replace(window)
        self.panels[2].top()
        self.panels[2].show()
        curses.panel.update_panels()
        self.screen.refresh()

        while self.getPressedCharacter() != 10:
            continue

        self.panels[2].hide()
        self.screen.refresh()

class Controller:
    DATABASE_FILE_NAME = "database.db"
    CREATE_TABLE_STATEMENT = "CREATE TABLE IF NOT EXISTS documents (content_hash text PRIMARY KEY, relative_path text NOT NULL UNIQUE, is_read INTEGER NOT NULL)"
    SELECT_ALL_STATEMENT = "SELECT * FROM documents ORDER BY relative_path ASC"

    def _checkIfDatabaseExists(self, path):
        return os.path.isfile(path)

    def _createDatabase(self, path):
        result = False

        try:
            connection = sqlite3.connect(path)
            connection.cursor().execute(self.CREATE_TABLE_STATEMENT)
            result = True
        except Exception:
            pass
        finally:
            connection.close()

        return result

    def _pathEndsWithSlash(self, path):
        return path.endswith("/")

    def _loadItemsFromDatabase(self, path):
        results = []

        try:
            connection = sqlite3.connect(path)
            cursor = connection.cursor()
            cursor.execute(self.SELECT_ALL_STATEMENT)
            results = cursor.fetchall()
        except Exception:
            pass
        finally:
            connection.close()

        return results

    def _listFiles(self, path):
        HASH_BUFFER_SIZE = 10 * 2**20 # 10MB
        filesList = dict()
        duplicatedFiles = [] # TODO MAKE LIST OF DUPLICATES AND SHOW IT
        includedExtensions = [".pdf", ".doc", ".docx", ".odt", ".mobi", ".epub", ".djvu", ".jpg", ".jpeg", ".png"]

        for path2, subdirs, files in os.walk(path):
            for name in files:
                add = False

                if name == self.DATABASE_FILE_NAME:
                    continue

                #for extension in includedExtensions:
                #    if name.lower().endswith(extension):
                #        add = True
                #        break
                add = True

                if add:
                    filePath = os.path.join(path2, name)
                    with open(filePath, 'rb') as file:
                        hash = hashlib.sha1()
                        while True:
                            data = file.read(HASH_BUFFER_SIZE)
                            if not data:
                                break
                            hash.update(data)
                        # TODO CHECK FOR DUPLICATES WITH FILE ON DISK AND RETURN INFO ABOUT THEM AND DON'T LOAD THEM
                        filesList[hash.hexdigest()] = filePath.replace(path, "")

        return filesList, duplicatedFiles

    def isDirectory(self, path):
        return os.path.isdir(path)

    def loadItems(self, libraryPath):
        if not self._pathEndsWithSlash(libraryPath):
            libraryPath = libraryPath + "/"

        databasePath = libraryPath + self.DATABASE_FILE_NAME

        if not self._checkIfDatabaseExists(databasePath):
            self._createDatabase(databasePath)

        databaseItems = self._loadItemsFromDatabase(databasePath)
        filesData, duplicatedFiles  = self._listFiles(libraryPath)

        databaseHashes = {}
        items = {} # {"fileHash": [False, False]} - first one if it exists in fileHashes, second if in database
        insertStatements = [] # TODO CHECKPOINT
        deleteStatements = []
        updateStatements = []

        for fileHash, filePath in filesData.items():
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
                insertStatements += [["INSERT INTO documents (relative_path, content_hash, is_read) VALUES (?, ?, 0)", filesData[fileHash], fileHash]]
                addedItems += 1

            if not info[0] and info[1]:
                deleteStatements += [["DELETE FROM documents WHERE content_hash=?", fileHash]]
                removedItems += 1

            if info[0] and info[1]:
                if filesData[fileHash] != databaseHashes[fileHash]:
                    updateStatements += [["UPDATE documents SET relative_path=? WHERE content_hash=?", filesData[fileHash], fileHash]]
                    movedItems += 1

        insertData(libraryPath, insertStatements)
        deleteData(libraryPath, deleteStatements)
        updateData(libraryPath, updateStatements)

        self.items = self._loadItemsFromDatabase(databasePath)

        return self.items, addedItems, removedItems, movedItems

    def getReadItems(self):
        return reduce((lambda a, b: a + b), list(map(lambda x: x[3], self.items)))

def main(screen):
    view = View(screen)
    controller = Controller()
    characterPressed = 0
    items = []
    position = 0
    startListPosition = 0
    endListPosition = 0
    readItems = 0
    libraryPath = ""

    while characterPressed != ord('x'):
        if True: #TODO REMOVE AND CHANGE INDENT
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
                if controller.isDirectory(libraryPath):
                    view.showReloadLibraryDialog()
                    [items, addedItems, removedItems, movedItems] = controller.loadItems(libraryPath)
                    readItems = controller.getReadItems()
                    view.hideReloadLibraryDialog()
                    view.showReloadSummaryDialog(addedItems, removedItems, movedItems)
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
#TODO HANDLE BETTER SCREEN SIZES (ALSO DIALOGS)
#TODO ADD INFO ABOUT INSUFFICIENT HEIGHT/WIDTH IF IT IS THE CASE
#TODO BASED ON ABOVE CALCULATE DIALOGS AT THE BEGINNING
#TODO ABSTRACT DIALOGS INTO NEW CLASS
#TODO IF TEXT DOESN'T FIT INTO DIALOG THEN SCROLL IT (ALSO STATUS BAR ETC.)
#TODO ADD POSSIBILITY FOR USER TO CHANGE FILES EXTENSION FILTER
#TODO ADD HANDLER FOR SITUATION WHERE THERE IS NO ITEMS IN DIRECTORY
#TODO ADD HANDLING FOR TWO FILES WITH SAME CONTENT AND DIFFERENT TITLES
