import os, os.path
import sqlite3
import hashlib
from functools import reduce

class Controller:
    DATABASE_FILE_NAME = "database.db"
    CREATE_TABLE_STATEMENT = "CREATE TABLE IF NOT EXISTS documents (content_hash text PRIMARY KEY, relative_path text NOT NULL, is_read INTEGER NOT NULL)"
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

        for path2, subdirs, files in os.walk(path):
            for name in files:
                add = False

                if name == self.DATABASE_FILE_NAME:
                    continue

                #TODO RETHINK IT - EXTENSION FILTER SHOULD ONLY FILTER VIEW OR ALSO ENTRIES IN DB?
                #for extension in self.extensions:
                #    if name.lower().endswith("." + extension):
                #        add = True
                #        break

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
            if not info[0] and info[1]:
                sqlStatements += [[self.DELETE_STATEMENT, {"content_hash": fileHash}]]
                removedItems += 1

            if info[0] and info[1]:
                if filesData[fileHash] != databaseHashes[fileHash]:
                    sqlStatements += [[self.UPDATE_PATH_STATEMENT, {"relative_path": filesData[fileHash], "content_hash": fileHash}]]
                    movedItems += 1

            if info[0] and not info[1]:
                sqlStatements += [[self.INSERT_STATEMENT, {"relative_path": filesData[fileHash], "content_hash": fileHash}]]
                addedItems += 1

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
        if len(self.items) > 0:
            self.items[position] = (self.items[position][0], self.items[position][1], self.items[position][2], int(not self.items[position][3]))
            sqlStatement = [[self.UPDATE_READ_STATUS_STATEMENT, {"is_read": self.items[position][3], "id": self.items[position][0]}]]
            self._executeSql(sqlStatement)

    def processExtensionsFilter(self, extensions):
        for extension in extensions.split(','):
            ext = extension.strip()
            if ext:
                self.extensions.append(ext)
