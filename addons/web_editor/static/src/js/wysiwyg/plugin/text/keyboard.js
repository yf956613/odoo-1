(function () {
'use strict';

we3.addPlugin('Keyboard', class extends we3.AbstractPlugin {
    static get autoInstall () {
        return [];
    }
    constructor () {
        super(...arguments);
        this.dependencies = ['Arch', 'Range', 'Paragraph', 'Link', 'History', 'Table']; // TODO: Remove dependencies
        this.editableDomEvents = {
            'keydown': '_onKeydown',
            'textInput': '_onTextInput',
            // 'DOMNodeInserted editable span': '_removeGarbageSpans',
        };
        this.tab = '\u00A0\u00A0\u00A0\u00A0';
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Handle the recording of history steps on character input.
     *
     * @param {String} key
     */
    _handleCharInputHistory (key) {
        var self = this;

        clearTimeout(this.lastCharIsVisibleTime);

        var stopChars = [' ', ',', ';', ':', '?', '.', '!'];
        var history = null; //this.dependencies.History.getHistoryStep();

        var isStopChar = stopChars.indexOf(key) !== -1;
        var isTopOfHistoryStack = !history || history.stack.length ||
            history.stackOffset >= history.stack.length - 1;

        if (isStopChar || !isTopOfHistoryStack) {
            this.lastCharVisible = false;
        }
        this.lastCharIsVisibleTime = setTimeout(function () {
            self.lastCharIsVisible = false;
        }, 500);
        if (!this.lastCharIsVisible) {
            this.lastCharIsVisible = true;
            // this.dependencies.History.recordUndo();
        }
    }
    /**
     * Handle deletion (BACKSPACE / DELETE).
     *
     * @private
     * @param {Boolean} isPrev true to delete BEFORE the carret
     * @returns {Boolean} true if case handled
     */
    _handleDeletion (isPrev) {
        this.dependencies.Arch[isPrev ? 'removeLeft' : 'removeRight']();
    }
    /**
     * Move to next cell on tab in a cell
     *
     * @param {ArchNode} scArch
     * @param {Boolean} untab true to move left
     */
    _handleTabInCell (scArch, untab) {
        var cell = scArch.ancestor('isCell');
        var nextCell = cell[untab ? 'previousSibling' : 'nextSibling']();
        if (!nextCell) {
            return;
        }
        var leaf = nextCell[untab ? 'lastLeaf' : 'firstLeaf']();
        this.dependencies.Range.setRange({
            scID: leaf.id,
            so: untab ? leaf.length() : 0,
        });
    }
    /**
     * Insert a TAB (4 non-breakable spaces).
     *
     * @private
     */
    _insertTab () {
        this.dependencies.Arch.insert(this.tab);
    }
    _isOffsetLeftEdge (range) {
        var pointArch = this._skipVirtual({
            archNode: range.scArch,
            offset: range.so,
        });
        return !pointArch.offset && range.isCollapsed() && pointArch.archNode
    }
    _isOnLeftEdgeOf (ancestorOrMethodName, range) {
        var ancestor = typeof ancestorOrMethodName === 'string' ? range.scArch.ancestor(ancestorOrMethodName) : ancestorOrMethodName;
        return ancestor && range.scArch.isLeftEdgeOf(ancestor, true) && this._isOffsetLeftEdge(range);
    }
    _skipVirtual (pointArch) {
        if (pointArch.archNode.isVirtual()) {
            pointArch.archNode = pointArch.archNode.nextUntil(pointArch.archNode.isNotVirtual);
            pointArch.offset = 0;
        }
        return pointArch;
    }
    /**
     * Patch for Google Chrome's contenteditable SPAN bug.
     *
     * @private
     * @param {jQueryEvent} e
     */
    /* _removeGarbageSpans (e) {
        if (e.target.className === "" && e.target.tagName == "SPAN" &&
            e.target.style.fontStyle === "inherit" &&
            e.target.style.fontVariantLigatures === "inherit" &&
            e.target.style.fontVariantCaps === "inherit") {
            var $span = $(e.target);
            $span.after($span.contents()).remove();
        }
    } */
    /**
     * Select all the contents of the current unbreakable ancestor.
     */
    _selectAll () {
        var self = this;
        var range = this.dependencies.Range.getRange();
        var unbreakable = range.scArch.ancestor('isUnbreakableNode');
        var $contents = $(unbreakable).contents();
        var startNode = $contents.length ? $contents[0] : unbreakable;
        var pointA = this.getPoint(startNode, 0);
        pointA = pointA.nextUntil(function (point) {
            return self.utils.isVisibleText(point.node);
        });
        var endNode = $contents.length ? $contents[$contents.length - 1] : unbreakable;
        var endOffset = $contents.length ? this.utils.nodeLength($contents[$contents.length - 1]) : 1;
        var pointB = this.getPoint(endNode, endOffset);
        pointB = pointB.prevUntil(function (point) {
            return self.utils.isVisibleText(point.node);
        });
        if (pointA && pointB) {
            range.replace({
                sc: pointA.node,
                so: pointA.offset,
                ec: pointB.node,
                eo: pointB.offset,
            }).normalize();
            range = this.dependencies.Arch.setRange(range.getPoints());
            this.dependencies.Arch.setRange(range);
        }
    }


    //--------------------------------------------------------------------------
    // Handle
    //--------------------------------------------------------------------------

    /** 
     * Customize handling of certain keydown events.
     *
     * @private
     * @param {SummernoteEvent} se
     * @param {Event} e
     * @returns {Boolean} true if case handled
     */
    _onKeydown (e) {
        var isNavKey = e.keyCode >= 33 && e.keyCode <= 40;
        var isSelectAll = e.ctrlKey && e.key === 'a';
        if (e.defaultPrevented || isNavKey || isSelectAll) {
            return;
        }

        var handled = false;
        var isChar = e.key && e.key.length === 1;
        var isAccented = e.key && (e.key === "Dead" || e.key === "Unidentified");
        var isModified = e.ctrlKey || e.altKey || e.metaKey;
        if ((isChar || isAccented) && !isModified) {
            if (isAccented) {
                this._accented = isAccented;
            }
            this._handleCharInputHistory(e.key);
        } else {
            this.lastCharIsVisible = false;
            switch (e.keyCode) {
                case 8: // BACKSPACE
                    handled = this._onBackspace(e);
                    break;
                case 9: // TAB
                    handled = this._onTab(e);
                    break;
                case 13: // ENTER
                    handled = this._onEnter(e);
                    break;
                case 46: // DELETE
                    handled = this._onDelete(e);
                    break;
            }
            if (handled) {
                e.preventDefault();
            }
        }
        if (e.key !== "Dead") {
            this._accented = false;
        }
    }
    /**
     * Handle BACKSPACE keydown event.
     *
     * @private
     * @returns {Boolean} true if case is handled and event default must be prevented
     */
    _onBackspace () {
        var range = this.dependencies.Range.getRange();
        if (!this._isOnLeftEdgeOf('isCell', range)) { // Do nothing if on left edge of a table cell
            this._handleDeletion(true)
        }
        return true;
    }
    /**
     * Handle DELETE keydown event.
     *
     * @private
     * @returns {Boolean} true if case is handled and event default must be prevented
     */
    _onDelete () {
        var range = this.dependencies.Range.getRange();

        // Special case
        if (range.isCollapsed()) {
            // Do nothing if on left edge of a table cell
            if (false && range.getStartPoint().isRightEdgeOfTag('TD')) {
                return true;
            }
        }

        this._handleDeletion(false);
        return true;
    }
    /**
     * Handle ENTER keydown event.
     *
     * @private
     * @param {KeyboardEvent} e
     * @returns {Boolean} true if case is handled and event default must be prevented
     */
    _onEnter (e) {
        if (e.shiftKey) {
            this.dependencies.Arch.insert('<br/>');
        } else if (e.ctrlKey) {
            this.dependencies.Arch.insert('<hr/>');
        } else {
            var range = this.dependencies.Range.getRange();
            var liAncestor = range.scArch.ancestor('isLi');
            var isInEmptyLi = range.isCollapsed() && liAncestor && liAncestor.isDeepEmpty();
            if (isInEmptyLi) {
                this.dependencies.Arch.outdent();
            } else {
                this.dependencies.Arch.addLine();
            }
        }
        return true;
    }
    /**
     * Handle TAB keydown event.
     *
     * @private
     * @param {KeyboardEvent} e
     * @returns {Boolean} true if case is handled and event default must be prevented
     */
    _onTab (e) {
        var handled = true;
        var untab = !!e.shiftKey;
        var range = this.dependencies.Range.getRange();
        if (range.scArch.isInCell()) {
            this._handleTabInCell(range.scArch, untab);
        } else if (!untab) {
            this._insertTab();
        } else {
            handled = false;
        }
        return handled;
    }
    /**
     * Handle visible char keydown event.
     *
     * @private
     * @param {TextEvent} ev
     */
    _onTextInput (ev) {
        ev.preventDefault();
        this._handleCharInputHistory(ev.data);
        var text;
        if (ev.data === ' ') {
            text = this.utils.char('nbsp');
        } else if (ev.data.charCodeAt(0) === 10) {
            text = '<br/>';
        } else {
            text = ev.data;
        }
        this.dependencies.Arch.insert(text);
    }
});

})();
