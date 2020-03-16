import os, os.path
import sqlite3
import hashlib
from functools import reduce
from concurrent.futures import ThreadPoolExecutor, as_completed

class Controller:
    DATABASE_FILE_NAME = "database.db"

    CREATE_DOCUMENTS_TABLE_STATEMENT = "CREATE TABLE IF NOT EXISTS documents (content_hash text PRIMARY KEY, relative_path text NOT NULL, is_read INTEGER NOT NULL)"
    SELECT_ALL_DOCUMENTS_STATEMENT = "SELECT * FROM documents ORDER BY relative_path ASC"
    INSERT_DOCUMENT_STATEMENT = "INSERT INTO documents (relative_path, content_hash, is_read) VALUES (:relative_path, :content_hash, 0)"
    DELETE_DOCUMENT_STATEMENT = "DELETE FROM documents WHERE content_hash=:content_hash"
    UPDATE_DOCUMENT_PATH_STATEMENT = "UPDATE documents SET relative_path=:relative_path WHERE content_hash=:content_hash"
    UPDATE_DOCUMENT_READ_STATUS_STATEMENT = "UPDATE documents SET is_read=:is_read WHERE id=:id"

    CREATE_CONFIG_TABLE_STATEMENT = "CREATE TABLE IF NOT EXISTS config (key text PRIMARY KEY, value text)"
    CREATE_CONFIG_ENTRIES_STATEMENT = "INSERT INTO config VALUES ('extensions', '')"
    SELECT_CONFIG_EXTENSIONS_STATEMENT = "SELECT value FROM config WHERE key='extensions'"
    UPDATE_CONFIG_EXTENSIONS_STATEMENT = "UPDATE config SET value=:extensions WHERE key='extensions'"

    HASH_BUFFER_SIZE = 10 * 2**20 # 10MB

    def __init__(self):
        self.items = []
        self.extensions = []
        self.databasePath = ""

    def _checkIfDatabaseExists(self, path):
        return os.path.isfile(path)

    def _createDatabase(self, path):
        result = False

        try:
            connection = sqlite3.connect(path)
            connection.cursor().execute(self.CREATE_DOCUMENTS_TABLE_STATEMENT)
            connection.cursor().execute(self.CREATE_CONFIG_TABLE_STATEMENT)
            connection.cursor().execute(self.CREATE_CONFIG_ENTRIES_STATEMENT)
            result = True
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
            cursor.execute(self.SELECT_ALL_DOCUMENTS_STATEMENT)
            results = cursor.fetchall()
        finally:
            connection.close()

        return results

    def _loadExtensionsFromDatabase(self):
        results = []

        try:
            connection = sqlite3.connect(self.databasePath)
            cursor = connection.cursor()
            cursor.execute(self.SELECT_CONFIG_EXTENSIONS_STATEMENT)
            for ext in cursor.fetchone()[0].split(","):
                if ext:
                    results.append(ext)
        finally:
            connection.close()

        return results

    def _saveExtensionsInDatabase(self):
        result = True

        try:
            connection = sqlite3.connect(self.databasePath)
            connection.cursor().execute(self.UPDATE_CONFIG_EXTENSIONS_STATEMENT, {"extensions": ",".join(self.extensions)})
            connection.commit()
        finally:
            connection.close()

        return result

    def _listFiles(self, path):
        filesList = dict()
        duplicatedFiles = [] # TODO MAKE LIST OF DUPLICATES AND SHOW IT
        tasks = []

        with ThreadPoolExecutor(max_workers = 50) as executor:
            for path2, subdirs, files in os.walk(path):
                for name in files:
                    add = False

                    if name == self.DATABASE_FILE_NAME:
                        continue

                    if len(self.extensions) == 0:
                        add = True
                    else:
                        for extension in self.extensions:
                            if name.lower().endswith("." + extension):
                                add = True
                                break

                    if add:
                        filePath = os.path.join(path2, name)
                        tasks.append(executor.submit(self._calculateHash, filePath, path))

            for task in as_completed(tasks):
                # TODO CHECK FOR DUPLICATES WITH FILE ON DISK AND RETURN INFO ABOUT THEM AND DON'T LOAD THEM
                result = task.result()
                filesList[result[0]] = result[1]

        return filesList, duplicatedFiles

    def _calculateHash(self, filePath, libraryPath):
        with open(filePath, 'rb') as file:
            hash = hashlib.sha1()
            while True:
                data = file.read(self.HASH_BUFFER_SIZE)
                if not data:
                    break
                hash.update(data)

            return [hash.hexdigest(), filePath.replace(libraryPath, "")]

    def _executeSql(self, sqlStatements):
        result = True

        try:
            connection = sqlite3.connect(self.databasePath)

            for statement in sqlStatements:
                connection.cursor().execute(statement[0], statement[1])

            connection.commit()
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

        self.extensions = self._loadExtensionsFromDatabase()
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
                sqlStatements += [[self.DELETE_DOCUMENT_STATEMENT, {"content_hash": fileHash}]]
                removedItems += 1

            if info[0] and info[1]:
                if filesData[fileHash] != databaseHashes[fileHash]:
                    sqlStatements += [[self.UPDATE_DOCUMENT_PATH_STATEMENT, {"relative_path": filesData[fileHash], "content_hash": fileHash}]]
                    movedItems += 1

            if info[0] and not info[1]:
                sqlStatements += [[self.INSERT_DOCUMENT_STATEMENT, {"relative_path": filesData[fileHash], "content_hash": fileHash}]]
                addedItems += 1

        self._executeSql(sqlStatements)

        self.items = self._loadItemsFromDatabase(self.databasePath)

        return self.items, addedItems, removedItems, movedItems

    def getNumberOfItems(self):
        return len(self.items)

    def listEmpty(self):
        return len(self.items) == 0

    def getItems(self):
        return self.items

    def getReadItems(self):
        return 0 if not self.items else reduce((lambda a, b: a + b), list(map(lambda x: x[3], self.items)))

    def changeReadState(self, position):
        if len(self.items) > 0:
            self.items[position] = (self.items[position][0], self.items[position][1], self.items[position][2], int(not self.items[position][3]))
            sqlStatement = [[self.UPDATE_DOCUMENT_READ_STATUS_STATEMENT, {"is_read": self.items[position][3], "id": self.items[position][0]}]]
            self._executeSql(sqlStatement)

    def processExtensionsFilter(self, extensions):
        self.extensions = []
        for extension in extensions.split(','):
            ext = extension.strip()
            if ext:
                self.extensions.append(ext)

        if self._checkIfDatabaseExists(self.databasePath):
            self._saveExtensionsInDatabase()

    def getExtensions(self):
        return self.extensions
