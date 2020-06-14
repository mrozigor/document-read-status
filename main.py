#!/bin/env python3

import curses
from view import View
from controller import Controller
from consts import KeyConsts

def main(screen):
    view = View(screen)
    controller = Controller()
    characterPressed = 0

    while characterPressed != KeyConsts.EXIT:
        if (characterPressed == KeyConsts.DOWN) and not controller.listEmpty():
            view.moveDown(controller.getNumberOfItems())
        elif (characterPressed == KeyConsts.UP) and not controller.listEmpty():
            view.moveUp(controller.getNumberOfItems())
        elif (characterPressed == KeyConsts.RIGHT) and not controller.listEmpty():
            view.moveScreenDown(controller.getNumberOfItems())
        elif (characterPressed == KeyConsts.LEFT) and not controller.listEmpty():
            view.moveScreenUp()
        elif characterPressed == KeyConsts.RELOAD_DATABASE:
            if controller.isDirectory(view.getLibraryPath()):
                view.showReloadLibraryDialog()
                [addedItems, removedItems, movedItems] = controller.loadItems(view.getLibraryPath())
                view.hideReloadLibraryDialog()
                view.showReloadSummaryDialog(addedItems, removedItems, movedItems)
            else:
                view.showLibraryPathIsNotDirectoryDialog()
        elif characterPressed == KeyConsts.SELECT_LIBRARY_PATH:
            view.showLibrarySelectionDialog()
            if controller.isDirectory(view.getLibraryPath()):
                controller.loadItemsFromDatabase(view.getLibraryPath())
            else:
                view.showLibraryPathIsNotDirectoryDialog()
        elif characterPressed == KeyConsts.CHANGE_READ_STATE:
            controller.changeReadState(view.getPosition())
        elif characterPressed == KeyConsts.APPLY_EXTENSION_FILTER:
            selectedExtensions = view.showExtensionsDialog(controller.getExtensions())
            controller.processExtensionsFilter(selectedExtensions)

        view.drawScreen(controller.getItems(), controller.getReadItems())

        characterPressed = view.getPressedCharacter()

if __name__ == "__main__":
    curses.wrapper(main)

#TODO HANDLE BETTER SCREEN SIZES (ALSO DIALOGS)
#TODO ADD INFO ABOUT INSUFFICIENT HEIGHT/WIDTH IF IT IS THE CASE
#TODO BASED ON ABOVE CALCULATE DIALOGS AT THE BEGINNING
#TODO ABSTRACT DIALOGS INTO NEW CLASS
#TODO IF TEXT DOESN'T FIT INTO DIALOG THEN SCROLL IT (ALSO STATUS BAR ETC.)
#TODO ADD HANDLING FOR TWO FILES WITH SAME CONTENT AND DIFFERENT TITLES
#TODO ADD SEARCH FUNCTION
#TODO REDRAW WHOLE SCREEN ONLY WHEN SIZE CHANGED
#TODO FIX NUMBERS COLUMN WHEN FILTERING IS ON
#TODO FILTERS ONLY SHOW GIVEN EXTENSION FILES FROM DB (BUT ALL FILES ARE SAVED IN DB)
