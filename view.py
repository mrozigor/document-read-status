import curses, curses.panel, curses.ascii

class View:
    STATUS_BAR = " e(x)it | (c)hange library path | change (e)xtensions filter | (r)eload | (SPC) read/unread | Read items: {}/{}"
    ITEMS_LIST_HEADER = " Number | Is read? | Path"

    def __init__(self, screen):
        self.libraryPath = ""
        self.position = 0
        self.startListPosition = 0
        self.endListPosition = 0
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

    def _drawItems(self, items, selectedItem):
        index = 1
        for item in items:
            if item == selectedItem:
                self.screen.attron(curses.color_pair(1))
            self.screen.addstr(index, 0, "{:^8}|{:^10}| {}".format(self.startListPosition + index, ("*" if item[3] == 1 else ""), item[1]))
            if item == selectedItem:
                self.screen.attroff(curses.color_pair(1))
            index = index + 1

    def getPressedCharacter(self):
        return self.screen.getch()

    def drawScreen(self, items, readItems):     
        self.screen.clear()
        self.height, self.width = self.screen.getmaxyx()

        if len(items) > 0:
            if (self.height - 2) != (self.endListPosition - self.startListPosition):
                self.endListPosition = (self.startListPosition + (self.height - 3))
                if self.position > self.endListPosition:
                    self.endListPosition = self.position
                    self.startListPosition = self.endListPosition - (self.height - 3)
            if self.endListPosition >= len(items):
                self.endListPosition = len(items) - 1
                self.startListPosition = self.endListPosition - (self.height - 3)
        
        # Items list
        self.screen.attron(curses.color_pair(1))
        self.screen.addstr(0, 0, self.ITEMS_LIST_HEADER)
        self.screen.addstr(0, len(self.ITEMS_LIST_HEADER), " " * (self.width - len(self.ITEMS_LIST_HEADER) - 1))
        self.screen.attroff(curses.color_pair(1))
        if len(items) > 0:
            self._drawItems(items[self.startListPosition:(self.endListPosition + 1)], items[self.position])

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

    def showLibraryPathIsNotDirectoryDialog(self):
        window = curses.newwin(7, 37, int(self.height - 0.5 * self.height - 4), int(self.width / 2 - 17))
        window.attron(curses.color_pair(2))
        window.box()
        window.addstr(1, 1, "".ljust(35, " "))
        window.addstr(2, 1, "".ljust(35, " "))
        window.addstr(3, 1, "    Given path is not directory    ")
        window.addstr(4, 1, "".ljust(35, " "))
        window.addstr(5, 1, "".ljust(35, " "))
        window.attroff(curses.color_pair(2))
        self.windows[1] = window
        self.panels[1].replace(window)
        self.panels[1].top()
        self.panels[1].show()
        curses.panel.update_panels()
        self.screen.refresh()
        while self.getPressedCharacter() != 10:
            continue
        self.panels[1].hide()

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

    def moveDown(self, numberOfItems):
        self.position = ((self.position + 1) % numberOfItems)
        if self.position > self.endListPosition:
            self.startListPosition = self.startListPosition + 1
            self.endListPosition = self.endListPosition + 1
        if self.position < self.startListPosition:
            self.startListPosition = self.position
            self.endListPosition = self.position

    def moveUp(self, numberOfItems):
        self.position = ((self.position - 1) % numberOfItems)
        if self.position < self.startListPosition:
            self.startListPosition = self.startListPosition - 1
            self.endListPosition = self.endListPosition - 1
        if self.position > self.endListPosition:
            self.startListPosition = self.position
            self.endListPosition = self.position

    def moveScreenDown(self, numberOfItems):
        delta = self.endListPosition - self.startListPosition
        if (self.endListPosition + delta) > numberOfItems:
            self.endListPosition = numberOfItems - 1
            self.startListPosition = self.endListPosition - delta
            self.position = self.endListPosition
        else:
            self.startListPosition = self.startListPosition + delta
            self.endListPosition = self.endListPosition + delta
            self.position = self.startListPosition

    def moveScreenUp(self):
        delta = self.endListPosition - self.startListPosition
        if (self.startListPosition - delta) < 0:
            self.startListPosition = 0
            self.endListPosition = self.startListPosition + delta
        else:
            self.startListPosition = self.startListPosition - delta
            self.endListPosition = self.endListPosition - delta
        self.position = self.startListPosition

    def getPosition(self):
        return self.position

    def showExtensionsDialog(self):
        selectedExtensions = ""
        window = curses.newwin(3, 80, int(self.height - 0.5 * self.height - 4), int(self.width / 2 - 40))
        window.attron(curses.color_pair(2))
        window.box()
        window.addstr(1, 1, "Extenstions filter (comma separated): ".ljust(78, " "))
        window.attroff(curses.color_pair(2))
        self.windows[3] = window
        self.panels[3].replace(window)
        self.panels[3].top()
        self.panels[3].show()
        curses.panel.update_panels()
        self.screen.refresh()
        characterPressed = 0

        while characterPressed != 10:
            characterPressed = self.getPressedCharacter()
            if characterPressed == curses.KEY_BACKSPACE:
                selectedExtensions = selectedExtensions[:-1]
            else:
                try:
                    selectedExtensions += chr(characterPressed)
                except ValueError:
                    pass

            self.windows[3].attron(curses.color_pair(2))
            self.windows[3].addstr(1, 1, "Extenstions filter (comma separated): " + selectedExtensions.ljust(int(80 - 2 - 38), " "))
            self.windows[3].attroff(curses.color_pair(2))
            curses.panel.update_panels() # TODO IS THIS REALLY NECESSARY?
            self.screen.refresh()

        self.panels[3].hide()
        
        return selectedExtensions
