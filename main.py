#!/bin/env python3

import sys
import curses
import os
import os.path
import sqlite3
from functools import reduce

def draw(stdscr):
    characterPressed = 0
    items = []
    position = 0
    startListPosition = 0
    endListPosition = 0
    readItems = 0
    libraryPath = ""
    changeLibraryPathMode = False

    # Clear and refresh the screen for a blank canvas
    stdscr.clear()
    stdscr.refresh()
    curses.curs_set(0)

    # Start colors in curses
    curses.start_color()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)

    while True:
        if characterPressed == 27:
            changeLibraryPathMode = False

        if changeLibraryPathMode:
            if characterPressed == curses.KEY_BACKSPACE:
                libraryPath = libraryPath[:-1]
            else:
                libraryPath += chr(characterPressed)
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
            elif characterPressed == ord('x'):
                break
            elif characterPressed == ord('r'):
                if os.path.isdir(libraryPath):
                    stdscr.addstr(1, 1, libraryPathHeader + "  Reloading...")
                    stdscr.refresh()
                    if libraryPath[len(libraryPath) - 1] != "/":
                        libraryPath = libraryPath + "/"

                    if not checkIfDatabaseExists(libraryPath):
                        createDatabase(libraryPath)

                    databaseItems = getItemsFromDatabase(libraryPath)
                    insertStatements = []

                    for filePath in listFiles(libraryPath):
                        found = False

                        for databaseItem in databaseItems:
                            if databaseItem[1] == filePath:
                                found = True
                                break

                        if not found:
                            insertStatements += [["INSERT INTO documents (relative_path, is_read) VALUES (?, 0)", filePath]]

                    insertData(libraryPath, insertStatements)

                    items = getItemsFromDatabase(libraryPath)
                    readItems = reduce((lambda a, b: a + b), list(map(lambda x: x[2], items)))
            elif characterPressed == ord('c'):
                changeLibraryPathMode = True
            elif characterPressed == ord(' '):
                if len(items) > 0:
                    items[position] = (items[position][0], items[position][1], int(not items[position][2]))
                    updateDocument(libraryPath, items[position])
                    readItems = reduce((lambda a, b: a + b), list(map(lambda x: x[2], items)))
            elif characterPressed == ord('l'):
                if os.path.isdir(libraryPath):
                    stdscr.addstr(1, 1, libraryPathHeader + "  Cleaning...")
                    stdscr.refresh()

                    if libraryPath[len(libraryPath) - 1] != "/":
                        libraryPath = libraryPath + "/"

                    if checkIfDatabaseExists(libraryPath):
                        databaseItems = getItemsFromDatabase(libraryPath)
                        deleteStatements = []

                        for databaseItem in databaseItems:
                            found = False

                            for filePath in listFiles(libraryPath):
                                if databaseItem[1] == filePath:
                                    found = True
                                    break

                            if not found:
                                deleteStatements += [["DELETE FROM documents WHERE id=?", databaseItem[0]]]

                        deleteData(libraryPath, deleteStatements)

                        items = getItemsFromDatabase(libraryPath)
                        readItems = reduce((lambda a, b: a + b), list(map(lambda x: x[2], items)))

        stdscr.clear()
        height, width = stdscr.getmaxyx()

        if len(items) > 0:
            if (height - 6) != (endListPosition - startListPosition):
                endListPosition = (startListPosition + (height - 6))
                if position > endListPosition:
                    endListPosition = position
                    startListPosition = endListPosition - (height - 6)
            if endListPosition >= len(items):
                endListPosition = len(items) - 1
                startListPosition = endListPosition - (height - 6)

        libraryPathHeader = "Path to library: " + libraryPath
        stdscr.addstr(1, 1, libraryPathHeader)
        if changeLibraryPathMode:
            stdscr.attron(curses.color_pair(1))
            stdscr.addstr(1, 1 + len(libraryPathHeader), " ")
            stdscr.attroff(curses.color_pair(1))

        # Items list
        itemsListHeader = " Number | Is read? | Path"
        stdscr.attron(curses.color_pair(1))
        stdscr.addstr(3, 0, itemsListHeader)
        stdscr.addstr(3, len(itemsListHeader), " " * (width - len(itemsListHeader) - 1))
        stdscr.attroff(curses.color_pair(1))
        if len(items) > 0:
            drawItems(stdscr, items[startListPosition:(endListPosition + 1)], items[position], startListPosition)

        # Status bar
        statusbarstr = " e(x)it | (c)hange library path / (ESC) return | (r)eload | c(l)ean not existing entries | (SPC) mark read/unread | Read items: {}/{}".format(readItems, len(items))
        stdscr.attron(curses.color_pair(1))
        stdscr.addstr(height - 1, 0, statusbarstr)
        stdscr.addstr(height - 1, len(statusbarstr), " " * (width - len(statusbarstr) - 1))
        stdscr.attroff(curses.color_pair(1))

        # Refresh the screen
        stdscr.refresh()
        # Wait for next input
        characterPressed = stdscr.getch()

def main():
    curses.wrapper(draw)

def listFiles(directory):
    filesList = []
    includedExtensions = [".pdf", ".doc", ".docx", ".odt", ".mobi", ".epub"]

    if os.path.isdir(directory):
        for path, subdirs, files in os.walk(directory):
            for name in files:
                add = False

                if name == "database.db":
                    continue

                for extension in includedExtensions:
                    if name.lower().endswith(extension):
                        add = True
                        break

                if add:
                    filesList += [os.path.join(path, name).replace(directory, "")]

    return filesList

def createDatabase(directory):
    result = False

    try:
        connection = sqlite3.connect(directory + "database.db")
        connection.cursor().execute("CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY, relative_path text NOT NULL UNIQUE, is_read INTEGER NOT NULL)")
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
            connection.cursor().execute(statement[0], [statement[1]])
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
    index = 0
    for item in items:
        if item == selectedItem:
            screen.attron(curses.color_pair(1))
        screen.addstr(index + 4, 0, "{:^8}|{:^10}| {}".format(startPosition + index, ("*" if item[2] == 1 else ""), item[1]))
        if item == selectedItem:
            screen.attroff(curses.color_pair(1))
        index = index + 1

def updateDocument(directory, document):
    result = False

    try:
        connection = sqlite3.connect(directory + "database.db")
        connection.cursor().execute("UPDATE documents SET is_read = ? WHERE id = ?", [document[2], document[0]])
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
#TODO ASK FOR MOVED FILES
#TODO HANDLE BETTER SCREEN SIZES
#TODO REFACTOR INSERTING AND DELETING DATA CODE
#TODO ADD POSSIBILITY FOR USER TO CHANGE FILES EXTENSION FILTER
