(function () {
'use strict';

var utils = we3.utils;

//--------------------------------------------------------------------------
// Size button
//--------------------------------------------------------------------------

we3.addPlugin('Float', class extends we3.AbstractPlugin {
    constructor () {
        super(...arguments);
        this.dependencies = ['Arch'];
        this.buttons = {
            template: 'we3.buttons.align',
            active: '_active',
            enabled: '_enabled',
        };
    }
    update (float, archNode) {
        archNode.className.remove('mx-auto pull-right pull-left');
        if (float === 'center') {
            archNode.className.add('mx-auto');
        } else if (float !== 'none') {
            archNode.className.add('pull-' + float);
        }
        this.dependencies.Arch.importUpdate(archNode.toJSON());
    }
    _active (buttonName, focusNode) {
        switch (buttonName) {
            case 'align-left': return focusNode.className.contains('pull-left');
            case 'align-center': return focusNode.className.contains('mx-auto');
            case 'align-right': return focusNode.className.contains('pull-right');
            case 'align-none':  return !(focusNode.className.contains('pull-left') || focusNode.className.contains('mx-auto') || focusNode.className.contains('pull-right'));
        }
    }
    _enabled (buttonName, focusNode) {
        return !focusNode.isText();
    }
});

//--------------------------------------------------------------------------
// Size button
//--------------------------------------------------------------------------

we3.addPlugin('MediaSize', class extends we3.AbstractPlugin {
    constructor () {
        super(...arguments);
        this.dependencies = ['Arch'];
        this.templatesDependencies = ['xml/media.xml'];
        this.buttons = {
            template: 'we3.buttons.size',
            active: '_active',
            enabled: '_enabled',
        };
    }

    update (size, archNode) {
        archNode.style.add('width', size === 'auto' ? '' : size);
        this.dependencies.Arch.importUpdate(archNode.toJSON());
    }

    _active (buttonName, focusNode) {
        var size = buttonName.split('-')[1];
        if (size === 'auto') {
            size = '';
        }
        return (focusNode.style.width ? focusNode.style.width.replace('%', '') : '') ===  size;
    }
    _enabled (buttonName, focusNode) {
        return focusNode.isMedia && focusNode.isMedia();
    }
});

//--------------------------------------------------------------------------
// Padding button
//--------------------------------------------------------------------------

we3.addPlugin('Padding', class extends we3.AbstractPlugin {
    constructor () {
        super(...arguments);
        this.dependencies = ['Arch'];
        this.templatesDependencies = ['xml/media.xml'];
        this.buttons = {
            template: 'we3.buttons.padding',
            active: '_active',
            enabled: '_enabled',
        };
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    update (value, archNode) {
        archNode.className = archNode.className.toString().replace(/(\s+)?padding-\S+/, '');
        archNode.className.add(value);
        this.dependencies.Arch.importUpdate(archNode.toJSON());
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _active (buttonName, focusNode) {
        return focusNode.className.contains(buttonName);
    }
    _enabled (buttonName, focusNode) {
        return !focusNode.isText();
    }
    _getButtonValues (method) {
        return this.buttons.$el.find('[data-method="' + method + '"][data-value]').map(function () {
            return $(this).attr('[data-value]');
        }).get();
    }
});

//--------------------------------------------------------------------------
// Alt update description
//--------------------------------------------------------------------------

we3.addPlugin('Alt', class extends we3.AbstractPlugin {
    constructor () {
        super(...arguments);
        this.templatesDependencies = ['xml/media.xml'];
        this.dependencies = ['Arch', 'Modal'];
        this.buttons = {
            template: 'we3.buttons.image.alt',
            enabled: '_enabled',
        };
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    alt (value, archNode) {
        var fragment = this._renderTemplate('we3.modal.media.alt', {
            archNode: archNode,
        });

        var title = this.options.translate('Media', 'Change media description and tooltip');
        var buttons = [{
            text: this.options.translate('Media', 'Save'),
            click: this._onClickSave.bind(this, archNode),
            className: 'we3-primary',
        }, {
            text: this.options.translate('Media', 'Discard'),
        }];
        this._modalId = this.dependencies.Modal.add(this.pluginName, title, fragment, buttons, function onClose() {
            self._modalId = null;
        });
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _enabled (buttonName, focusNode) {
        return focusNode.isImg && focusNode.isImg();
    }

    _onClickSave (archNode) {
        var modal = this.dependencies.Modal.get(this._modalId);
        archNode.attributes.alt = modal.querySelector('input#alt').value;
        archNode.attributes.title = modal.querySelector('input#title').value;
        this.dependencies.Arch.importUpdate(archNode.toJSON());
    }
});

//--------------------------------------------------------------------------
// Media & add media modal
//--------------------------------------------------------------------------

we3.addPlugin('Media', class extends we3.AbstractPlugin {
    /**
     * @override
     */
    constructor (parent, params) {
        super(...arguments);
        this.templatesDependencies = ['xml/media.xml'];
        this.dependencies = ['Arch', 'Range', 'Renderer', 'Rules', 'Modal'];
        this.editableDomEvents = {
            'dblclick': '_onDblclick',
        };
        this.buttons = {
            template: 'we3.buttons.media',
        };
        this._panels = [];
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Open the image dialog and listen to its saved/closed events.
     */
    addMedia (value, archNode) {
        return new Promise(this._createModal.bind(this, archNode.ancestor('isMedia')));
    }
    /**
     *
     * @param {string} title
     * @param {function} callback
     *      returns Promise({active: boolean, content: DocumentFragment})
     * @param {function} onSave
     *      return a Promise resolved by DOM element or JSON
     **/
    addPanel (name, title, renderPanel, onSave, priority) {
        this._panels.push({
            text: title,
            renderPanel: renderPanel,
            onSave: onSave,
            priority: priority,
            name: name,
        });
        this._panels.sort(function (a, b) { return a.priority - b.priority; });
    }
    getArchNode (archNode) {
        return archNode.ancestor('isMedia');
    }
    /**
     * Remove the current target media and hide its popover.
     */
    removeMedia (value, archNode) {
        var mediaArchNode = archNode.ancestor('isMedia');
        if (mediaArchNode) {
            this.dependencies.Arch.remove(mediaArchNode.id);
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _createModal (mediaArchNode, resolve) {
        if (this._modalId) {
            return resolve && resolve();
        }
        var self = this;
        var title = this.options.translate('Media', 'Select a Media');
        return this._createModalContent(mediaArchNode).then(function (fragment) {
            var buttons = [{
                text: self.options.translate('Media', mediaArchNode ? 'Save' : 'Add'),
                click: self._onClickSave.bind(self, mediaArchNode),
                className: 'we3-primary',
            }, {
                text: self.options.translate('Media', 'Cancel'),
            }];
            self._modalId = self.dependencies.Modal.add(self.pluginName, title, fragment, buttons, function onClose () {
                self._modalId = null;
                resolve && resolve();
            });
        });
    }
    _createModalContent (mediaArchNode) {
        var self = this;
        var promises = [];
        var fragment = this._renderTemplate('we3.modal.media');
        var tablist = fragment.querySelector('we3-tablist');
        var tabpanels = fragment.querySelector('we3-tabpanels');

        tabpanels.addEventListener('dblclick', self._onDoubleClickPanel.bind(self, mediaArchNode), false);

        var hasActive = false;
        var panels = [];

        this._panels.forEach(function (tab, index) {
            var res = tab.renderPanel(mediaArchNode);
            var button = document.createElement('we3-button');
            button.setAttribute('role', 'tab');
            button.setAttribute('name', tab.name);
            button.textContent = tab.text;
            button.addEventListener('click', self._onClickTab.bind(self), false);

            var tabpanel = document.createElement('we3-tabpanel');
            tabpanel.setAttribute('role', 'tabpanel');
            tabpanel.appendChild(res.content);

            if (!hasActive && res.active) {
                tabpanel.classList.add('active');
                button.classList.add('active');
                hasActive = true;
            }
            panels[index] = [button, tabpanel];
        });

        return Promise.all(promises).then(function () {
            panels.forEach(function (panel) {
                tablist.appendChild(panel[0]);
                tabpanels.appendChild(panel[1]);
            });
            if (!hasActive) {
                var tabpanel = tabpanels.querySelector('we3-tabpanel');
                if (tabpanel) {
                    tabpanel.classList.add('active');
                    tablist.querySelector('we3-button').classList.add('active');
                }
            }
            return fragment;
        });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onClickSave (mediaArchNode) {
        var self = this;
        var modal = this.dependencies.Modal.get(this._modalId);
        var tabpanels = modal.querySelector('we3-tabpanels');
        var activePanel = tabpanels.querySelector('we3-tabpanel.active');
        var pluginOnSave = this._panels[[].indexOf.call(tabpanels.children, activePanel)].onSave;
        pluginOnSave(activePanel).then(function (media) {
            console.log('TODO use', mediaArchNode);
            if (mediaArchNode) {
                self.dependencies.Range.setRange({
                    scID: mediaArchNode.parent.id,
                    so:   mediaArchNode.index() + 1,
                });
                self.dependencies.Arch.insert(media);
                self.dependencies.Arch.remove(mediaArchNode.id);
            } else {
                self.dependencies.Arch.insert(media);
            }
        });
    }
    _onDblclick (ev) {
        var id = this.dependencies.Renderer.getID(ev.target);
        var mediaArchNode = id && this.dependencies.Arch.getClonedArchNode(id).ancestor('isMedia', true);
        if (mediaArchNode) {
            ev.preventDefault();
            ev.stopPropagation();
            this._createModal(mediaArchNode, null);
        }
    }
    _onDoubleClickPanel (mediaArchNode, ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this._onClickSave(mediaArchNode);
        this.dependencies.Modal.remove(this._modalId);
    }
    _onClickTab (ev) {
        var tablist = ev.target.parentNode;
        var tabpanels = tablist.nextElementSibling;
        var active = tablist.querySelector('.active');
        if (active !== ev.target) {
            active.classList.remove('active');
            tabpanels.querySelector('.active').classList.remove('active');
        }
        ev.target.classList.add('active');
        var index = [].indexOf.call(tablist.childNodes, ev.target);
        tabpanels.childNodes[index].classList.add('active');
    }
});

var Media = class extends we3.ArchNode {
    isVoidoid () {
        return true;
    }
    isMedia () {
        return true;
    }
    removeLeft () {
        this.remove();
    }
    removeRight () {
        this.remove();
    }
    split () {
        return;
    }
};

//--------------------------------------------------------------------------
// Image
//--------------------------------------------------------------------------

we3.addPlugin('Image', class extends we3.AbstractPlugin {
    constructor () {
        super(...arguments);
        this.templatesDependencies = ['xml/media.xml'];
        this.dependencies = ['Arch', 'Media'];
        this.buttons = {
            template: 'we3.buttons.image',
            active: '_active',
        };
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    displayRecord (record) {
        var img = document.createElement('img');
        img.setAttribute('title', record.title || record.name);
        img.setAttribute('alt', record.alt);
        img.setAttribute('src', record.url);
        img.className = record.className || '';
        return img;
    }
    getArchNode (archNode) {
        return archNode.ancestor('isImg');
    }
    toggleClass (value, archNode) {
        archNode.className.toggle(value);
        this.dependencies.Arch.importUpdate(archNode.toJSON());
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _active (buttonName, focusNode) {
        return focusNode.className.contains(buttonName);
    }
});
we3.addPlugin('ImageUrl', class extends we3.AbstractPlugin {
    static get autoInstall () {
        return ['Media', 'Image'];
    }
    constructor () {
        super(...arguments);
        this.dependencies = ['Arch', 'Media'];
        this.templatesDependencies = ['xml/media.xml'];
    }
    start () {
        var title = this.options.translate('ImageUrl', 'Image');
        this.dependencies.Media.addPanel('image', title, this._renderMediaTab.bind(this), this._onSaveMedia.bind(this), 10);
        return super.start();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    createForm () {
        return this._renderTemplate('we3.modal.media.image');
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _renderMediaTab (mediaArchNode) {
        return {
            active: mediaArchNode && mediaArchNode.isImg && mediaArchNode.isImg(),
            content: this.createForm(),
        };
    }

    //--------------------------------------------------------------------------
    // Handle
    //--------------------------------------------------------------------------

    _onSaveMedia (panel) {
        debugger
    }
    _onURLInputChange (value, ev) {
        var form = ev.target.closest('form');
        this._updateURLInputbuttons(form);
    }
    _onURLButtonClick (value, ev) {
        var form = ev.target.closest('form');
        var input = ev.target.previousElementSibling;
        var ext = input.value.split('.').pop();
        var records = [{
            alt: input.value,
            url: input.value,
            selected: true,
            mimetype: 'application/' + ext,
        }];
        input.value = '';
        this._updateURLInputbuttons(form);
        this._addDocuments(form, records);
    }
});

we3.addArchNode('img', class extends Media {
    isImg () {
        return true;
    }
    isInline () {
        return true;
    }
    get type () {
        return 'img';
    }
});

//--------------------------------------------------------------------------
// Media Document
//--------------------------------------------------------------------------

we3.addPlugin('Document', class extends we3.AbstractPlugin {
    getArchNode (archNode) {
        return archNode.ancestor('isDocument');
    }
    displayRecord (record) {
        var a = document.createElement('a');
        a.setAttribute('title', record.title || record.name);
        a.setAttribute('data-mimetype', record.mimetype);
        var ext = record.url.match(/\.([a-z0-9]+)$/i);
        if (ext) {
            ext = ext[1];
            a.setAttribute('data-ext', ext.toLowerCase());
        }
        a.setAttribute('href', record.url);
        a.setAttribute('target', '_BLANK');
        a.className = record.className || '';
        a.classList.add('we3-document');

        var img = document.createElement('img');
        var mimetype = 'unknown';
        var mimetypes = we3.utils.defaults(this.options.Media.mimetypes, we3.options.Media.mimetypes);
        for (var m in mimetypes) {
            if (mimetypes[m].mimetype.test(record.mimetype) || ext && mimetypes[m].ext && mimetypes[m].ext.test(ext)) {
                mimetype = m;
                break;
            }
        }
        img.setAttribute('src', this.options.xhrPath + 'img/mimetypes/' + mimetype + '.svg');
        img.classList.add('we3-document-image');
        a.appendChild(img);
        return a;
    }
});
we3.addPlugin('DocumentUrl', class extends we3.AbstractPlugin {
    static get autoInstall () {
        return ['Media', 'Document'];
    }
    constructor () {
        super(...arguments);
        this.dependencies = ['Arch', 'Media'];
        this.templatesDependencies = ['xml/media.xml'];
    }
    start () {
        var title = this.options.translate('DocumentUrl', 'Document');
        this.dependencies.Media.addPanel('document-url', title, this._renderMediaTab.bind(this), this._onSaveMedia.bind(this), 20);
        return super.start();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _renderMediaTab (mediaArchNode) {
        return {
            active: mediaArchNode && mediaArchNode.isImg && mediaArchNode.isImg(),
            content: this._renderTemplate('we3.modal.media.document'),
        };
    }

    //--------------------------------------------------------------------------
    // Handle
    //--------------------------------------------------------------------------

    _onSaveMedia (panel) {
        debugger
    }
});

var DOCUMENT = class extends Media {
    //--------------------------------------------------------------------------
    // static
    //--------------------------------------------------------------------------

    static parse (archNode, options) {
        var isDocument = archNode.nodeName === 'a' && (archNode.className.contains('we3-document') || archNode.attributes['data-mimetype']);
        if (isDocument) {
            return new DOCUMENT(archNode.params, archNode.nodeName, archNode.attributes.toJSON());
        }
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    isDocument () {
        return true;
    }
    isInline () {
        return true;
    }
    get type () {
        return 'DOCUMENT';
    }
}
we3.addArchNode('DOCUMENT', DOCUMENT);

we3.options.Media = {
    mimetypes: {
        image: {
            mimetype: /^image|(png$)/,
            ext: /gif|jpe|jpg|png/,
        },
        audio: {
            mimetype: /^audio/,
        },
        binary: {
            mimetype: /octet-stream|download|python/,
            ext: /py/,
        },
        video: {
            mimetype: /^video/,
            ext: /avi|mp4/,
        },
        archive: {
            mimetype: /(zip|package)|(archive$)|(tar$)|(compressed$)/,
            ext: /zip|tar|rar/,
        },
        pdf: {
            mimetype: /pdf$/,
            ext: /pdf/,
        },
        document: {
            mimetype: /(^text-master)|document|msword|wordprocessing/,
            ext: /docx?|odt|ott|uot|fodt/,
        },
        web_code: {
            mimetype: /xml|html/,
            ext: /xml|htm|html|xhtml/,
        },
        web_style: {
            mimetype: /(less|css)$/,
            ext: /less|css/,
        },
        text: {
            mimetype: /(^text)|(rtf$)/,
            ext: /rtf|txt/,
        },
        disk: {
            mimetype: /-image|diskimage/,
            ext: /dmg/,
        },
        spreadsheet: {
            mimetype: /csv|vc|excel|mods|spreadsheet|(numbers$)|(calc$)/,
            ext: /csv|xlsx?|ots|ods|uos|fods/,
        },
        certificate: {
            mimetype: /(^key)|cert|rules|pkcs|(stl$)|(crl$)/,
        },
        presentation: {
            mimetype: /presentation|keynote|teacher|slideshow|powerpoint/,
            ext: /pptx?|ppsx|potm|pptm|otp|odp|uop|fodp/,
        },
        font: {
            mimetype: /-font|font-/,
            ext: /ttf/,
        },
        print: {
            mimetype: /-dvi/,
        },
        script: {
            mimetype: /script|x-sh|(bat$)|(cgi$)|(-c$)|java|ruby/,
            ext: /bat/,
        },
        javascript: {
            mimetype: /javascript/,
            ext: /js/,
        },
        calendar: {
            mimetype: /calendar|(ldif$)/,
            ext: /ical|ics|ifb|icalendar/,
        },
        vector: {
            mimetype: /svg|((postscript|cdr|xara|cgm|graphics|draw)$)/,
            ext: /svg/,
        },
    },
};

//--------------------------------------------------------------------------
// Pictogram
//--------------------------------------------------------------------------

we3.addPlugin('Pictogram', class extends we3.AbstractPlugin {
    /**
     *
     * @param {Object} parent
     * @param {Object} params
     * @param {object} [params.pictogram] @see _computeFonts
     */
    constructor () {
        super(...arguments);
        this.templatesDependencies = ['xml/media.xml'];
        this.dependencies = ['Arch', 'Media'];
        this.buttons = {
            template: 'we3.buttons.pictogram',
        };
        this.iconsParser = this.options.pictogram.map(function (picto) {
            return {
                base: picto.base,
                cssParser: new RegExp('\\.(' + picto.parser + ')::?before', 'i'),
            };
        });
    }
    /**
     * @override
     */
    start () {
        var title = this.options.translate('Pictogram', 'Pictogram');
        this.dependencies.Media.addPanel('pictogram', title, this._renderMediaTab.bind(this), this._onSaveMedia.bind(this), 30);
        return super.start();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    getArchNode (archNode) {
        return archNode.ancestor('isPictogram');
    }
    toggleClass (value, archNode) {
        archNode.className.toggle(value);
        this.dependencies.Arch.importUpdate(archNode.toJSON());
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Searches the fonts described
     *
     * @private
     * @param {object[]} fontIcons
     *   List of font icons to load by editor. The icons are displayed in the media
     *   editor and identified like font and image (can be colored, spinned, resized
     *   with fa classes).
     *   To add font, push a new object {base, parser}
     *
     *   - base: class who appear on all fonts
     *   - parser: string to create the regular expression used to select all font
     *           in css stylesheets and the regular expression for parsing
     *
     * @type Array
     */
    _computeFonts () {
        var self = this;
        this.cacheCssSelectors = {};
        this.iconsParser.forEach(function (data) {
            data.cssData = self._getCssSelectors(data.cssParser);
            data.alias = utils.flatten(data.cssData.map(function (cssData) {
                return cssData.names;
            }));
        });
        this.alias = utils.flatten(this.iconsParser.map(function (data) {
            return data.alias;
        }));
    }
    _displayPictogram (documents, iconsParser) {
        documents.innerHTML = '';
        iconsParser.forEach(function (data) {
            data.cssData.forEach(function (cssData) {
                var doc = document.createElement('we3-document');
                doc.setAttribute('data-id', cssData.names[0]);
                doc.setAttribute('data-alias', cssData.names.join(','));
                var span = document.createElement('i');
                span.setAttribute('title', cssData.names[0]);
                span.setAttribute('aria-label', cssData.names[0]);
                span.setAttribute('role', 'img');
                span.classList.add(data.base);
                span.classList.add(cssData.names[0]);

                doc.appendChild(span);
                documents.appendChild(doc);
            });
        });
    }
    /**
     * Retrieves all the CSS rules which match the given parser (Regex).
     *
     * @private
     * @param {Regex} filter
     * @returns {Object[]} Array of CSS rules descriptions (objects). A rule is
     *          defined by 3 values: 'selector', 'css' and 'names'. 'selector'
     *          is a string which contains the whole selector, 'css' is a string
     *          which contains the css properties and 'names' is an array of the
     *          first captured groups for each selector part. E.g.: if the
     *          filter is set to match .fa-* rules and capture the icon names,
     *          the rule:
     *              '.fa-alias1::before, .fa-alias2::before { hello: world; }'
     *          will be retrieved as
     *              {
     *                  selector: '.fa-alias1::before, .fa-alias2::before',
     *                  css: 'hello: world;',
     *                  names: ['.fa-alias1', '.fa-alias2'],
     *              }
     */
    _getCssSelectors (filter) {
        if (this.cacheCssSelectors[filter]) {
            return this.cacheCssSelectors[filter];
        }
        this.cacheCssSelectors[filter] = [];
        var sheets = document.styleSheets;
        for (var i = 0; i < sheets.length; i++) {
            var rules;
            try {
                // try...catch because Firefox not able to enumerate
                // document.styleSheets[].cssRules[] for cross-domain
                // stylesheets.
                rules = sheets[i].rules || sheets[i].cssRules;
            } catch (e) {
                console.warn("Can't read the css rules of: " + sheets[i].href, e);
                continue;
            }
            if (!rules) {
                continue;
            }

            for (var r = 0 ; r < rules.length ; r++) {
                var selectorText = rules[r].selectorText;
                if (!selectorText) {
                    continue;
                }
                var selectors = selectorText.split(/\s*,\s*/);
                var data = null;
                for (var s = 0; s < selectors.length; s++) {
                    var match = selectors[s].trim().match(filter);
                    if (!match) {
                        continue;
                    }
                    if (!data) {
                        data = {
                            selector: match[0],
                            css: rules[r].cssText.replace(/(^.*\{\s*)|(\s*\}\s*$)/g, ''),
                            names: [match[1]]
                        };
                    } else {
                        data.selector += (', ' + match[0]);
                        data.names.push(match[1]);
                    }
                }
                if (data) {
                    this.cacheCssSelectors[filter].push(data);
                }
            }
        }
        return this.cacheCssSelectors[filter];
    }
    /**
     * @private
     */
    _getFont (classNames) {
        if (!(classNames instanceof Array)) {
            classNames = (classNames || "").split(/\s+/);
        }
        var fontIcon, cssData;
        for (var k = 0; k < this.iconsParser.length; k++) {
            fontIcon = this.iconsParser[k];
            for (var s = 0; s < fontIcon.cssData.length; s++) {
                cssData = fontIcon.cssData[s];
                if (_.intersection(classNames, cssData.names).length) {
                    return {
                        base: fontIcon.base,
                        cssParser: fontIcon.cssParser,
                        font: cssData.names[0],
                    };
                }
            }
        }
        return null;
    }
    _renderMediaTab (mediaArchNode) {
        if (!this.cacheCssSelectors) {
            this._computeFonts();
        }
        var fragment = this._renderTemplate('we3.modal.media.pictogram');
        var iconsParser = this._searchPictogram(null);
        var documents = fragment.querySelector('we3-documents');
        this._displayPictogram(documents, iconsParser);

        var pictogram = mediaArchNode && mediaArchNode.isPictogram && mediaArchNode.isPictogram() && mediaArchNode;
        if (pictogram) {
            // documents.querySelector('.');
        }

        return {
            active: !!pictogram,
            content: fragment,
        };
    }
    _searchPictogram (needle) {
        var iconsParser = this.iconsParser;
        if (needle && needle.length) {
            iconsParser = [];
            this.iconsParser.forEach(function (data) {
                var cssData = data.cssData.filter(function (cssData) {
                    return cssData.names.filter(function (alias) {
                        return alias.indexOf(needle) >= 0;
                    })[0];
                });
                if (cssData.length) {
                    iconsParser.push({
                        base: data.base,
                        cssData: cssData,
                    });
                }
            });
        }
        return iconsParser;
    }

    //--------------------------------------------------------------------------
    // Handle
    //--------------------------------------------------------------------------

    _onSaveMedia (panel) {
        return new Promise(function (resolve) {
            resolve(panel.querySelector('we3-document.we3-selected').firstChild);
        });
    }
    _onSearch (value, ev) {
        var documents = ev.target.closest('we3-group.we3-pictogram').querySelector('we3-documents');
        var iconsParser = this._searchPictogram(ev.target.value);
        this._displayPictogram(documents, iconsParser);
    }
    _onSelectDocument (value, ev) {
        var doc = ev.srcElement.closest('we3-document');
        var selected = doc.closest('we3-group.we3-pictogram').querySelector('we3-document.we3-selected');
        if (selected) {
            selected.classList.remove('we3-selected');
        }
        doc.classList.add('we3-selected');
    }
});

var PICTOGRAM = class extends Media {
    //--------------------------------------------------------------------------
    // static
    //--------------------------------------------------------------------------

    static parse (archNode, options) {
        var iconsParser = options.pictogram || [];
        var isFont = false;
        var className = archNode.isNotText() && archNode.className.toString() || '';
        if (className) {
            iconsParser.forEach(function (picto) {
                var reg = utils.getRegex(picto.parser, 'i', '(^|\\s)(' + picto.parser + ')(\\s|$)');
                if (reg.test(className)) {
                    isFont = true;
                }
            });
        }
        if (isFont) {
            return new PICTOGRAM(archNode.params, archNode.nodeName, archNode.attributes.toJSON());
        }
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    isPictogram () {
        return true;
    }
    isInline () {
        return true;
    }
    get type () {
        return 'PICTOGRAM';
    }
};
we3.addArchNode('PICTOGRAM', PICTOGRAM);

//--------------------------------------------------------------------------
// Video
//--------------------------------------------------------------------------

we3.addPlugin('Video', class extends we3.AbstractPlugin {
    constructor () {
        super(...arguments);
        this.dependencies = ['Media'];

        this.featuresSelected = new Set();
        this.currentUrl = "";

        this._providers = {
            youtube: {
                features: {
                    autoplay: {},
                    loop: {},
                    controls: {default: true},
                    fs: {name: 'Fullscreen', default: true, depend: 'controls'},
                    modestbranding: {default: true, name: 'Logo', depend: 'controls'},
                },
                parseUrl: (url, options)=>{
                    const m = url.match(/^(?:(?:https?:)?\/\/)?(?:www\.)?(?:youtu\.be\/|youtube(-nocookie)?\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))((?:\w|-){11})(?:\S+)?$/);
                    return m && (m[2].length === 11) && ('//www.youtube' + (m[1] || '') + '.com/embed/' + m[2]);
                },
            },
            dailymotion: {
                features: {
                    autoplay: {},
                    'mute': {},
                    'ui-start-screen-info': {name: 'Start infos', default: true},
                    'queue-autoplay-next': {name: 'Queue next', default: true},
                    controls: {default: true},
                    'ui-logo': {name: 'Logo', default: true, depend: 'controls'},
                    'sharing-enable': {name: 'Sharing', default: true, depend: 'controls'},
                },
                parseUrl: (url, options)=>{
                    const m = url.match(/.+dailymotion.com\/(video|hub|embed)\/([^_]+)[^#]*(#video=([^_&]+))?/);
                    return m && m[2].length && ('//www.dailymotion.com/embed/video/' + m[2].replace('video/', ''));
                },
            },
            vimeo: {
                features: {
                    autoplay: {},
                    loop: {},
                },
                parseUrl: (url, options)=>{
                    const m = url.match(/\/\/(player.)?vimeo.com\/([a-z]*\/)*([0-9]{6,11})[?]?.*/);
                    return m && m[3].length && '//player.vimeo.com/video/' + m[3];
                },
            },
            instagram: {
                features: {},
                parseUrl: (url, options)=>{
                    const m = url.match(/(.*)instagram.com\/p\/(.[a-zA-Z0-9]*)/);
                    return m && m[2].length && ('//www.instagram.com/p/' + m[2] + '/embed/');
                },
            },
            vine: {
                features: {},
                parseUrl: (url, options)=>{
                    const m = url.match(/\/\/vine.co\/v\/(.[a-zA-Z0-9]*)/);
                    return m && m[0] && (m[0] + '/embed/simple');
                },
            },
            youku: {
                features: {},
                parseUrl: (url, options)=>{
                    const m = url.match(/(.*).youku\.com\/(v_show\/id_|embed\/)(.+)/);
                    if (m && m[3].length) {
                        const index = m[3].indexOf('.html?');
                        const id = index >= 0 ? m[3].substring(0, index) : m[3];
                        return '//player.youku.com/embed/' + id;
                    } else {
                        return false;
                    }
                },
            },
        };

    }

    /**
     * @override
     */
    start () {
        var title = this.options.translate('VideoUrl', 'Video');
        this.dependencies.Media.addPanel('video', title, this._renderMediaTab.bind(this), this._onSaveMedia.bind(this), 40);
        return super.start();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    getArchNode (archNode) {
        return archNode.ancestor('isVideo');
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Render the whole widget and add event on the textarea.
     *
     * @private
     * @param {ArchNode} mediaArchNode
     */
    _renderMediaTab (mediaArchNode) {
        this._fragment = this._renderTemplate('we3.modal.media.video');
        this._formControl = this._fragment.querySelector('.form-control');
        this._optionsContainer = this._fragment.querySelector('.o_video_dialog_options');
        this._videoContainer = this._fragment.querySelector('.media_iframe_video');
        this._formControl.addEventListener('keyup', this._updateVideoPreview.bind(this));
        return {
            active: mediaArchNode && mediaArchNode.isVideo && mediaArchNode.isVideo(),
            content: this._fragment,
        };
    }

    /**
     * Update the video options and preview.
     *
     * @private
     */
    _updateVideoPreview () {
        const code = this._formControl.value;
        const extractedUrl = this._extractEmbeded(code) || code;
        this.currentProvider = Object.values(this._providers)
                               .find((provider) => this.currentUrl = provider.parseUrl(extractedUrl));
        this._renderOptionElements(this.currentProvider);
        this._renderVideo();
    }

    /***
     * Extract an url from an embeded code.
     *
     * @param {string} code The code that might contain an url through src="<url>" or href="<url>"
     * @return {String|undefined} The extracted url if it found one. Otherwise return undefined.
     */
    _extractEmbeded (code) {
        var embedMatch = code.match(/(src|href)=["']?([^"']+)?/);
        if (embedMatch) {
            if (embedMatch[2].length > 0 && embedMatch[2].indexOf('instagram')) {
                return embedMatch[2]; // Instagram embed code is different
            } else {
                return embedMatch[1];
            }
        }
    }

    /***
     * Render the video preview.
     *
     */
    _renderVideo () {
        if (this.currentProvider) {
            const iframe = this._videoContainer.querySelector('iframe');
            if (iframe) {
                iframe.outerHTML = '';
            }
            this.videoElement = this._getVideo(this.currentProvider);
            this._videoContainer.appendChild(this.videoElement);
        }
    }

    /**
     * Create a video element from an url.
     * @param {string} url
     * @param {Object} options
     * @returns {Element} the constructed video element
     */
    _getVideo (provider, url, options) {
        const videoElement = document.createElement('iframe');
        videoElement.setAttribute('width', 1280);
        videoElement.setAttribute('height', 720);
        videoElement.setAttribute('frameborder', 0);
        videoElement.setAttribute('class', 'o_video_dialog_iframe');
        const optionsList = Object.keys(provider.features).map(featureKey => {
            return featureKey + '=' + (this.featuresSelected.has(featureKey) ? '1' : '0');
        });
        videoElement.setAttribute('src', this.currentUrl + '?' + optionsList.join('&'));
        return videoElement;
    }

    /***
     * Render the options of the video depending on the specified provider.
     *
     * @param {Object} rovider The provider object.
     */
    _renderOptionElements (provider) {
        this._optionsContainer.innerHTML = "";
        if (!provider) {
            return;
        }

        const inputElements = {};
        const depends = {};
        Object.keys(provider.features).forEach((featureKey)=>{
            const feature = provider.features[featureKey];
            const groupElement = this._getOptionElement(feature, featureKey);
            const inputElement = groupElement.querySelector('input');
            inputElements[featureKey] = inputElement;

            if (feature.depend) {
                if (!depends[feature.depend]) {
                    depends[feature.depend] = [groupElement];
                } else {
                    depends[feature.depend].push(groupElement);
                }
            }

            inputElement.addEventListener('click', (ev)=>{
                this._toggleFeature(featureKey, depends);
            });
            this._optionsContainer.appendChild(groupElement);
        });
    }

    /**
     * Get an option element that is rendered depending if it is selected or not.
     *
     * @param {Object} feature The feature object.
     * @param {String} featureKey The key.
     * @returns {HTMLElement} The option element.
     */
    _getOptionElement (feature, featureKey) {
        const groupElement = document.createElement('we3-group');
        const labelElement = document.createElement('label');
        labelElement.setAttribute('class', 'o_switch mb0');
        groupElement.appendChild(labelElement);
        const inputElement = document.createElement('input');
        if (feature.default === true) {
            inputElement.setAttribute('checked', true);
            this.featuresSelected.add(featureKey);
        } else {
            this.featuresSelected.delete(featureKey);
        }
        inputElement.setAttribute('type', 'checkbox');
        const featureName = feature.name || featureKey.charAt(0).toUpperCase() + featureKey.slice(1);
        const textElement = document.createTextNode(featureName);
        labelElement.appendChild(inputElement);
        labelElement.appendChild(document.createElement('span'));
        labelElement.appendChild(textElement);
        return groupElement;
    }

    /**
     * Toggle a feature with "key", while considering it's dependency.
     *
     * @param {String} featureKey The key feature to toggle.
     * @param {Object} depends An object where the key is the dependent feature name and the value,
     *                         the HTMLElement associated.
     */
    _toggleFeature (featureKey, depends) {
        if (this.featuresSelected.has(featureKey)) {
            this.featuresSelected.delete(featureKey);
            (depends[featureKey] || []).forEach((element)=>{
                element.style.display = 'none';
            });
        } else {
            this.featuresSelected.add(featureKey);
            (depends[featureKey] || []).forEach((element)=>{
                element.style.display = 'block';
            });
        }
        this._renderVideo();
    }

    //--------------------------------------------------------------------------
    // Handle
    //--------------------------------------------------------------------------

    _onSaveMedia (panel) {
        return new Promise(resolve => {
            resolve(this._videoContainer.outerHTML);
        });
    }
});

var VIDEO = class extends Media {
    //--------------------------------------------------------------------------
    // static
    //--------------------------------------------------------------------------

    static parse (archNode, options) {
        var isVideo = archNode.nodeName === 'div' && (archNode.className.contains('media_iframe_video'));
        if (isVideo) {
            return new VIDEO(archNode.params, archNode.nodeName, archNode.attributes);
        }
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    isBlock () {
        return true;
    }
    isVideo () {
        return true;
    }
    get type () {
        return 'VIDEO';
    }
};
we3.addArchNode('VIDEO', VIDEO);

//--------------------------------------------------------------------------
// Handle (hover image)
//--------------------------------------------------------------------------

// Make sure not to forget https://github.com/odoo/odoo/pull/31226 !!!
// var HandlePlugin = Plugins.handle.extend({
//     /**
//      * Update the handle.
//      *
//      * @param {Node} target
//      * @returns {Boolean}
//      */
//     update (target) {
//         if (this.context.isDisabled()) {
//             return false;
//         }
//         var isImage = this.utils.isImg(target);
//         var $selection = this.$handle.find('.note-control-selection');
//         this.context.invoke('imagePopover.update', target);
//         if (!isImage) {
//             return isImage;
//         }

//         var $target = $(target);
//         var pos = $target.offset();
//         var posContainer = $selection.closest('.note-handle').offset();

//         // exclude margin
//         var imageSize = {
//             w: $target.outerWidth(false),
//             h: $target.outerHeight(false)
//         };
//         $selection.css({
//             display: 'block',
//             left: pos.left - posContainer.left,
//             top: pos.top - posContainer.top,
//             width: imageSize.w,
//             height: imageSize.h,
//         }).data('target', $target); // save current target element.

//         var src = $target.attr('src');
//         var sizingText = imageSize.w + 'x' + imageSize.h;
//         if (src) {
//             var origImageObj = new Image();
//             origImageObj.src = src;
//             sizingText += ' (' + this.lang.image.original + ': ' + origImageObj.width + 'x' + origImageObj.height + ')';
//         }
//         $selection.find('.note-control-selection-info').text(sizingText);

//         return isImage;
//     },
// });

// we3.addPlugin('Handle', HandlePlugin);

})();
