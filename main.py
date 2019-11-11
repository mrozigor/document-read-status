#!/bin/env python3

import curses
from view import View
from controller import Controller

def main(screen):
    view = View(screen)
    controller = Controller()
    characterPressed = 0

    while characterPressed != ord('x'):
        if (characterPressed == curses.KEY_DOWN) and (controller.getNumberOfItems() != 0):
            view.moveDown(controller.getNumberOfItems())
        elif (characterPressed == curses.KEY_UP) and (controller.getNumberOfItems() != 0):
            view.moveUp(controller.getNumberOfItems())
        elif (characterPressed == curses.KEY_RIGHT) and (controller.getNumberOfItems() != 0):
            view.moveScreenDown(controller.getNumberOfItems())
        elif (characterPressed == curses.KEY_LEFT) and (controller.getNumberOfItems() != 0):
            view.moveScreenUp()
        elif characterPressed == ord('r'):
            if controller.isDirectory(view.getLibraryPath()):
                view.showReloadLibraryDialog()
                [items, addedItems, removedItems, movedItems] = controller.loadItems(view.getLibraryPath())
                view.hideReloadLibraryDialog()
                view.showReloadSummaryDialog(addedItems, removedItems, movedItems)
            else:
                view.showLibraryPathIsNotDirectoryDialog()
        elif characterPressed == ord('c'):
            view.showLibrarySelectionDialog()
        elif characterPressed == ord(' '):
            controller.changeReadState(view.getPosition())
        elif characterPressed == ord('e'):
            selectedExtensions = view.showExtensionsDialog(controller.getExtensions())
            controller.processExtensionsFilter(selectedExtensions)

        view.drawScreen(controller.getItems(), controller.getReadItems())

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
#TODO ADD SEARCH FUNCTION
#TODO MOVE CALCULATING HASHES TO THREADS
#TODO REDRAW WHOLE SCREEN ONLY WHEN SIZE CHANGED
