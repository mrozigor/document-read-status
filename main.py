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
        self.libraryPath = ""
        self.screen = screen
        self._initializeCurses()
        self._createPanels()

    def _initializeCurses(self):
        self.screen.clear()
        self.screen.refresh()
        curses.curs_set(0)

        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_WHITE)

    def _createPanels(self):
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

    def _drawItems(items, selectedItem, startPosition):
        index = 1
        for item in items:
            if item == selectedItem:
                self.screen.attron(curses.color_pair(1))
            self.screen.addstr(index, 0, "{:^8}|{:^10}| {}".format(startPosition + index, ("*" if item[3] == 1 else ""), item[1]))
            if item == selectedItem:
                self.screen.attroff(curses.color_pair(1))
            index = index + 1

    def getPressedCharacter(self):
        return self.screen.getch()

    def drawScreen(self, items, startListPosition, endListPosition, position, readItems):
        self.screen.clear()
        self.height, self.width = self.screen.getmaxyx()
        
        # Items list
        self.screen.attron(curses.color_pair(1))
        self.screen.addstr(0, 0, self.ITEMS_LIST_HEADER)
        self.screen.addstr(0, len(self.ITEMS_LIST_HEADER), " " * (self.width - len(self.ITEMS_LIST_HEADER) - 1))
        self.screen.attroff(curses.color_pair(1))
        if len(items) > 0:
            self._drawItems(items[startListPosition:(endListPosition + 1)], items[position], startListPosition)

        # Status bar
        statusBar = self.STATUS_BAR.format(readItems, len(items))
        self.screen.attron(curses.color_pair(1))
        self.screen.addstr(self.height - 1, 0, statusBar)
        self.screen.addstr(self.height - 1, len(statusBar), ("library: " + self.libraryPath + " ").rjust((self.width - len(statusBar) - 1), " "))
        self.screen.attroff(curses.color_pair(1))

        curses.panel.update_panels()
        self.screen.refresh()

    def showLibrarySelectionDialog(self):
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
                self.libraryPath = self.libraryPath[:-1]
            else:
                try:
                    self.libraryPath += chr(characterPressed)
                except ValueError:
                    pass

            self.windows[0].attron(curses.color_pair(2))
            self.windows[0].addstr(1, 1, "Path to library: " + self.libraryPath.ljust(int(self.width - 0.5 * self.width - 19), " "))
            self.windows[0].attroff(curses.color_pair(2))
            curses.panel.update_panels() # TODO IS THIS REALLY NECESSARY?
            self.screen.refresh()

            characterPressed = self.getPressedCharacter()

        self.panels[0].hide()
        curses.panel.update_panels()
        self.screen.refresh()

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

    def getLibraryPath(self):
        return self.libraryPath

class Controller:
    DATABASE_FILE_NAME = "database.db"
    CREATE_TABLE_STATEMENT = "CREATE TABLE IF NOT EXISTS documents (content_hash text PRIMARY KEY, relative_path text NOT NULL UNIQUE, is_read INTEGER NOT NULL)"
    SELECT_ALL_STATEMENT = "SELECT * FROM documents ORDER BY relative_path ASC"
    INSERT_STATEMENT = "INSERT INTO documents (relative_path, content_hash, is_read) VALUES (:relative_path, :content_hash, 0)"
    DELETE_STATEMENT = "DELETE FROM documents WHERE content_hash=:content_hash"
    UPDATE_PATH_STATEMENT = "UPDATE documents SET relative_path=:relative_path WHERE content_hash=:content_hash"
    UPDATE_READ_STATUS_STATEMENT = "UPDATE documents SET is_read=:is_read WHERE id=:id"

    def __init__(self):
        self.items = []

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

    def _loadItemsFromDatabase(self, databasePath):
        results = []

        try:
            connection = sqlite3.connect(databasePath)
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

    def _executeSql(self, sqlStatements):
        result = True

        try:
            connection = sqlite3.connect(self.databasePath)

            for statement in sqlStatements:
                connection.cursor().execute(statement[0], statement[1])

            connection.commit()
        except Exception:
            result = False
            pass
        finally:
            connection.close()

        return result

    def isDirectory(self, path):
        return os.path.isdir(path)

    def loadItems(self, libraryPath):
        if not self._pathEndsWithSlash(libraryPath):
            libraryPath = libraryPath + "/"

        self.databasePath = libraryPath + self.DATABASE_FILE_NAME

        if not self._checkIfDatabaseExists(self.databasePath):
            self._createDatabase(self.databasePath)

        databaseItems = self._loadItemsFromDatabase(self.databasePath)
        filesData, duplicatedFiles  = self._listFiles(libraryPath)

        databaseHashes = {}
        items = {} # {"fileHash" => [False, False]} - first one if hash exists in files, second if in database
        sqlStatements = []

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
                sqlStatements += [[self.INSERT_STATEMENT, {"relative_path": filesData[fileHash], "content_hash": fileHash}]]
                addedItems += 1

            if not info[0] and info[1]:
                sqlStatements += [[self.DELETE_STATEMENT, {"content_hash": fileHash}]]
                removedItems += 1

            if info[0] and info[1]:
                if filesData[fileHash] != databaseHashes[fileHash]:
                    sqlStatements += [[self.UPDATE_PATH_STATEMENT, {"relative_path": filesData[fileHash], "content_hash": fileHash}]]
                    movedItems += 1

        self._executeSql(sqlStatements)

        self.items = self._loadItemsFromDatabase(self.databasePath)

        return self.items, addedItems, removedItems, movedItems

    def getNumberOfItems(self):
        return len(self.items)

    def getItems(self):
        return self.items

    def getReadItems(self):
        return 0 if not self.items else reduce((lambda a, b: a + b), list(map(lambda x: x[3], self.items)))

    def changeReadState(self, position):
        if len(self.items) <= 0:
            return # TODO MAYBE CHECK OTHER WAY IF POSITION IS CORRECT?
        
        self.items[position][3] = int(not self.items[position][3])
        sqlStatement = [[self.UPDATE_READ_STATUS_STATEMENT, {"is_read": self.items[position][3], "id": self.items[position][0]}]]
        self._executeSql(sqlStatement)

def main(screen):
    view = View(screen)
    controller = Controller()
    characterPressed = 0
    position = 0
    startListPosition = 0
    endListPosition = 0

    while characterPressed != ord('x'):
        if (characterPressed == curses.KEY_DOWN) and (controller.getNumberOfItems() != 0):
            position = ((position + 1) % controller.getNumberOfItems())
            if position > endListPosition:
                startListPosition = startListPosition + 1
                endListPosition = endListPosition + 1
            if position < startListPosition:
                startListPosition = position
                endListPosition = position
        elif (characterPressed == curses.KEY_UP) and (controller.getNumberOfItems() != 0):
            position = ((position - 1) % controller.getNumberOfItems())
            if position < startListPosition:
                startListPosition = startListPosition - 1
                endListPosition = endListPosition - 1
            if position > endListPosition:
                startListPosition = position
                endListPosition = position
        elif (characterPressed == curses.KEY_RIGHT) and (controller.getNumberOfItems() != 0):
            delta = endListPosition - startListPosition
            if (endListPosition + delta) > controller.getNumberOfItems():
                endListPosition = controller.getNumberOfItems() - 1
                startListPosition = endListPosition - delta
                position = endListPosition
            else:
                startListPosition = startListPosition + delta
                endListPosition = endListPosition + delta
                position = startListPosition
        elif (characterPressed == curses.KEY_LEFT) and (controller.getNumberOfItems() != 0):
            delta = endListPosition - startListPosition
            if (startListPosition - delta) < 0:
                startListPosition = 0
                endListPosition = startListPosition + delta
            else:
                startListPosition = startListPosition - delta
                endListPosition = endListPosition - delta
            position = startListPosition
        elif characterPressed == ord('r'):
            if controller.isDirectory(view.getLibraryPath()):
                view.showReloadLibraryDialog()
                [items, addedItems, removedItems, movedItems] = controller.loadItems(view.getLibraryPath())
                view.hideReloadLibraryDialog()
                view.showReloadSummaryDialog(addedItems, removedItems, movedItems)
        elif characterPressed == ord('c'):
            view.showLibrarySelectionDialog()
        elif characterPressed == ord(' '):
            controller.changeReadState(position)

        if controller.getNumberOfItems() > 0:
            if (height - 2) != (endListPosition - startListPosition):
                endListPosition = (startListPosition + (height - 3))
                if position > endListPosition:
                    endListPosition = position
                    startListPosition = endListPosition - (height - 3)
            if endListPosition >= controller.getNumberOfItems():
                endListPosition = controller.getNumberOfItems() - 1
                startListPosition = endListPosition - (height - 3)

        view.drawScreen(controller.getItems(), startListPosition, endListPosition, position, controller.getReadItems())

        # Wait for next input
        characterPressed = view.getPressedCharacter()

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
