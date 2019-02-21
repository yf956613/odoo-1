odoo.define('wysiwyg.widgets.media', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');
var fonts = require('wysiwyg.fonts');
var utils = require('web.utils');
var Widget = require('web.Widget');
var concurrency = require('web.concurrency');

var QWeb = core.qweb;

var _t = core._t;

var ImagePreviewDialog = Dialog.extend({
    template: 'wysiwyg.widgets.image_preview',
    xmlDependencies: ['/web_editor/static/src/xml/wysiwyg.xml'],

    events: _.extend({}, Dialog.prototype.events, {
        'change .js_quality_range': '_onChangeQuality',
    }),
    /**
     * @constructor
     */
    init: function (parent, options, attachment, def) {
        this._super(parent, _.extend({}, {
            title: _t("Improve your Image"),
            buttons: [
                {text: _t("Optimize"), classes: 'btn-primary', close: true, click: this._onSave.bind(this)},
                {text: _t("Keep Original"), close: true}
            ],
        }, options));
        this.on('closed', this, this._onClose);

        this.attachment = attachment;
        this.defaultQuality = 80;
        this.def = def;

        this._onChangeQuality = _.debounce(this._onChangeQuality.bind(this));
    },
    /**
     * @override
     */
    start: function () {
        var defParent = this._super.apply(this, arguments);
        this.$previewImage = this.$('.js_preview_image');
        this.$qualityRange = this.$('.js_quality_range');
        this.$currentQuality = this.$('.js_current_quality');
        this.$currentSize = this.$('.js_current_size');
        this.$originalSize = this.$('.js_original_size');
        this.$filename = this.$('.o_we_filename');
        var defPreview = this._updatePreview();
        return $.when(defParent, defPreview);
    },
    /**
     * Requests a preview for the current settings and displays it.
     *
     * @private
     * @returns {Deferred}
     */
    _updatePreview: function () {
        var self = this;
        var quality = this.$qualityRange.val();
        // var base64Original = this.attachment..split(',')[1];
        return this._rpc({
            route: _.str.sprintf('/web_editor/attachment/%d/preview', this.attachment.id),
            params: {
                'quality': quality,
            }
        }).then(function (res) {
            self.$currentQuality.text(quality);
            self.$currentSize.text(utils.binaryToBinsize(res.image.split(',')[1]));
            // self.$originalSize.text(utils.binaryToBinsize(base64Original));
            // self.$previewImage.attr('src', self.attachment.url + '?quality=' + quality);
            self.$previewImage.attr('src', res.image);
        });
    },
    /**
     * Handles change of the quality setting: updates the preview to show the
     * result with the new quality.
     *
     * @private
     * @returns {Deferred}
     */
    _onChangeQuality: function () {
        return this._updatePreview();
    },
    /**
     * Handles clicking on the save button, which is resolving the deferred with
     * the current settings.
     * TODO SEB maybe just trigger up something instead.
     */
    _onSave: function () {
        this.def.resolve(this.$filename.val(), this.$currentQuality.val(), this.imageOriginal);
    },
    /**
     * Handles closing the modal. Does nothing if called after save, otherwise
     * rejects the deferred.
     */
    _onClose: function () {
        if (this.def.state() === 'pending') {
            this.def.reject();
        }
    },

});

var MediaWidget = Widget.extend({
    xmlDependencies: ['/web_editor/static/src/xml/wysiwyg.xml'],
    events: {
        'input input.o_we_search': '_onSearchInput',
    },

    /**
     * @constructor
     * @param {Element} media: the target Element for which we select a media
     * @param {Object} options: useful parameters such as res_id, res_model,
     *  context, user_id, ...
     */
    init: function (parent, media, options) {
        this._super.apply(this, arguments);
        this.media = media;
        this.$media = $(media);
        this._onSearchInput = _.debounce(this._onSearchInput, 500);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @todo comment
     */
    clear: function () {
        if (!this.media) {
            return;
        }
        this._clear();
    },
    /**
     * Finds and displays existing attachments related to the target media.
     *
     * @abstract
     * @param {string} needle: only return attachments matching this parameter
     * @returns {Deferred}
     */
    search: function (needle) {},
    /**
     * Saves the currently configured media on the target media.
     *
     * @abstract
     * @returns {*}
     */
    save: function () {},

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @abstract
     */
    _clear: function () {},

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onSearchInput: function (ev) {
        this.search($(ev.currentTarget).val() || '');
        this.hasSearched = true;
    },
});

/**
 * Let users choose an image, including uploading a new image in odoo.
 */
var ImageWidget = MediaWidget.extend({
    template: 'wysiwyg.widgets.image',
    events: _.extend({}, MediaWidget.prototype.events || {}, {
        'change .o_file_input': '_onChangeFileInput',
        'click .existing-attachments [data-src]': '_onImageClick',
        'click .o_existing_attachment_remove': '_onRemoveClick',
        'click .o_load_more': '_onLoadMoreClick',
        'click .o_upload_media_button': '_onUploadButtonClick',
        'click .o_upload_media_url_button': '_onUploadURLButtonClick',
        'dblclick .existing-attachments [data-src]': '_onImageDblClick',
        'input .o_we_url_input': '_onInputUrl',
    }),

    IMAGES_PER_ROW: 6,
    IMAGES_ROWS: 5,

    /**
     * @constructor
     */
    init: function (parent, media, options) {
        this._super.apply(this, arguments);
        this._mutex = new concurrency.Mutex();

        this.imagesRows = this.IMAGES_ROWS;

        this.options = options;
        this.context = options.context;
        this.accept = options.accept || (options.document ? '*/*' : 'image/*');

        this.multiImages = options.multiImages;

        this.firstFilters = options.firstFilters || [];
        this.lastFilters = options.lastFilters || [];

        this.records = [];
        this.selectedImages = [];
    },
    /**
     * Loads all the existing images related to the target media.
     *
     * @override
     */
    willStart: function () {
        return $.when(
            this._super.apply(this, arguments),
            this.search('', true)
        );
    },
    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        var self = this;
        this.$urlInput = this.$('.o_we_url_input');
        this.$form = this.$('form');
        this.$fileInput = this.$('.o_file_input');
        this.$uploadButton = this.$('.o_upload_media_button');
        this.$addUrlButton = this.$('.o_upload_media_url_button');
        this.$urlSuccess = this.$('.o_we_url_warning');
        this.$urlWarning = this.$('.o_we_url_success');
        this.$urlError = this.$('.o_we_url_error');
        this.$formText = this.$('.form-text');

        this._renderImages(true);

        // If there is already an image on the target, select by default that
        // image if it is among the loaded images.
        // TODO SEB improve this to also work for product image for example,
        // or any image where the url is not the attachment url but a field
        // for example based on res_id, checksum, etc.
        var o = {
            url: null,
            alt: null,
        };
        if (this.$media.is('img')) {
            o.url = this.$media.attr('src');
        } else if (this.$media.is('a.o_image')) {
            o.url = this.$media.attr('href').replace(/[?].*/, '');
            o.id = +o.url.match(/\/web\/content\/(\d+)/, '')[1];
        }
        if (o.url) {
            self._toggleImage(_.find(self.records, function (record) {
                return record.url === o.url;
            }) || o, true);
        }

        return def;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Saves the currently selected image on the target media. If new files are
     * currently being added, delays the save until all files have been added.
     *
     * @override
     */
    save: function () {
        return this._mutex.exec(this._save.bind(this));
    },
    /**
     * @override
     * @param {boolean} noRender: if true, do not render the found attachments
     */
    search: function (needle, noRender) {
        var self = this;
        return this._rpc({
            model: 'ir.attachment',
            method: 'search_read',
            args: [],
            kwargs: {
                domain: this._getAttachmentsDomain(needle),
                fields: ['name', 'datas_fname', 'mimetype', 'checksum', 'url', 'type', 'res_id', 'res_model', 'access_token'],
                order: [{name: 'id', asc: false}],
                context: this.context,
            },
        }).then(function (records) {
            self.records = _.chain(records)
                .filter(function (r) {
                    // TODO SEB do this in the domain
                    return (r.type === "binary" || r.url && r.url.length > 0);
                })
                .uniq(function (r) {
                    // TODO SEB try to do this in the domain
                    return (r.url || r.id);
                })
                .sortBy(function (r) {
                    // TODO SEB maybe we should make a route that takes care of this
                    if (_.any(self.firstFilters, function (filter) {
                        var regex = new RegExp(filter, 'i');
                        return r.name.match(regex) || r.datas_fname && r.datas_fname.match(regex);
                    })) {
                        return -1;
                    }
                    if (_.any(self.lastFilters, function (filter) {
                        var regex = new RegExp(filter, 'i');
                        return r.name.match(regex) || r.datas_fname && r.datas_fname.match(regex);
                    })) {
                        return 1;
                    }
                    return 0;
                })
                .value();

            _.each(self.records, function (record) {
                record.src = record.url || _.str.sprintf('/web/image/%s/%s', record.id, encodeURI(record.name)); // Name is added for SEO purposes
                record.isDocument = !(/gif|jpe|jpg|png/.test(record.mimetype));
            });
            if (!noRender) {
                self._renderImages();
            }
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _clear: function () {
        if (!this.$media.is('img')) {
            return;
        }
        var allImgClasses = /(^|\s+)((img(\s|$)|img-(?!circle|rounded|thumbnail))[^\s]*)/g;
        var allImgClassModifiers = /(^|\s+)(rounded-circle|shadow|rounded|img-thumbnail|mx-auto)([^\s]*)/g;
        this.media.className = this.media.className && this.media.className
            .replace('o_we_custom_image', '')
            .replace(allImgClasses, ' ')
            .replace(allImgClassModifiers, ' ');
    },
    /**
     * Returns the domain for attachments used in media dialog.
     * We look for attachments related to the current document. If there is a value for the model
     * field, it is used to search attachments, and the attachments from the current document are
     * filtered to display only user-created documents.
     * In the case of a wizard such as mail, we have the documents uploaded and those of the model
     *
     * @private
     * @params {string} needle
     * @returns {Array} "ir.attachment" odoo domain.
     */
    _getAttachmentsDomain: function (needle) {
        var domain = this.options.attachmentIDs && this.options.attachmentIDs.length ? ['|', ['id', 'in', this.options.attachmentIDs]] : [];

        var attachedDocumentDomain = [
            '&',
            ['res_model', '=', this.options.res_model],
            ['res_id', '=', this.options.res_id|0]
        ];
        // if the document is not yet created, do not see the documents of other users
        if (!this.options.res_id) {
            attachedDocumentDomain.unshift('&');
            attachedDocumentDomain.push(['create_uid', '=', this.options.user_id]);
        }
        if (this.options.data_res_model) {
            var relatedDomain = ['&',
                ['res_model', '=', this.options.data_res_model],
                ['res_id', '=', this.options.data_res_id|0]];
            if (!this.options.data_res_id) {
                relatedDomain.unshift('&');
                relatedDomain.push(['create_uid', '=', session.uid]);
            }
            domain = domain.concat(['|'], attachedDocumentDomain, relatedDomain);
        } else {
            domain = domain.concat(attachedDocumentDomain);
        }
        domain = ['|', ['public', '=', true]].concat(domain);

        domain.push('|',
            ['mimetype', '=', false],
            ['mimetype', this.options.document ? 'not in' : 'in', ['image/gif', 'image/jpe', 'image/jpeg', 'image/jpg', 'image/gif', 'image/png']]);
        if (needle && needle.length) {
            domain.push('|', ['datas_fname', 'ilike', needle], ['name', 'ilike', needle]);
        }
        domain.push('|', ['datas_fname', '=', false], '!', ['datas_fname', '=like', '%.crop'], '!', ['name', '=like', '%.crop']);
        return domain;
    },
    /**
     * Returns the total number of images that should be displayed, depending
     * on the number of images per row and the current number of rows.
     *
     * @private
     * @returns {integer} the number of images to display
     */
    _getNumberOfImagesToDisplay: function () {
        return this.IMAGES_PER_ROW * this.imagesRows;
    },
    /**
     * @private
     */
    _highlightSelectedImages: function () {
        var self = this;
        this.$('.o_existing_attachment_cell.o_selected').removeClass("o_selected");
        var $select = this.$('.o_existing_attachment_cell [data-src]').filter(function () {
            var $img = $(this);
            return !!_.find(self.selectedImages, function (v) {
                return (v.url === $img.data("src") || ($img.data("url") && v.url === $img.data("url")) || v.id === $img.data("id"));
            });
        });
        $select.closest('.o_existing_attachment_cell').addClass("o_selected");
        return $select;
    },
    /**
     * @private
     */
    _loadMoreImages: function (forceSearch) {
        this.imagesRows += 2;
        if (!forceSearch) {
            this._renderImages();
        } else {
            this.search(this.$('.o_we_search').val() || '');
        }
    },
    /**
     * @private
     */
    _renderImages: function (withEffect) {
        var self = this;
        var rows = _(this.records).chain()
            .slice(0, this._getNumberOfImagesToDisplay())
            .groupBy(function (a, index) {
                return Math.floor(index / self.IMAGES_PER_ROW);
            })
            .values()
            .value();

        this.$('.form-text').empty();

        // Render menu & content
        this.$('.existing-attachments').replaceWith(
            QWeb.render('wysiwyg.widgets.files.existing.content', {
                rows: rows,
                isDocument: this.options.document,
                withEffect: withEffect,
            })
        );

        var $divs = this.$('.o_image');
        var imageDefs = _.map($divs, function (el) {
            var $div = $(el);
            if (/gif|jpe|jpg|png/.test($div.data('mimetype'))) {
                var $img = $('<img/>', {
                    class: 'img-fluid',
                    src: $div.data('url') || $div.data('src'),
                });
                var def = $.Deferred();
                $img[0].onload = def.resolve.bind(def);
                $div.addClass('o_webimage').append($img);
                return def;
            }
        });
        if (withEffect) {
            $.when.apply($, imageDefs).then(function () {
                _.delay(function () {
                    $divs.removeClass('o_image_loading');
                }, 400);
            });
        }
        this._highlightSelectedImages();

        // adapt load more
        var noMoreImgToLoad = this._getNumberOfImagesToDisplay() >= this.records.length;
        this.$('.o_load_more').toggleClass('d-none', noMoreImgToLoad);
        this.$('.o_load_done_msg').toggleClass('d-none', !noMoreImgToLoad);
    },
    /**
     * @private
     */
    _save: function () {
        var self = this;
        if (this.multiImages) {
            return this.selectedImages;
        }

        var img = this.selectedImages[0];
        if (!img) {
            return this.media;
        }

        var def = $.when();
        if (!img.access_token) {
            def = this._rpc({
                model: 'ir.attachment',
                method: 'generate_access_token',
                args: [[img.id]]
            }).then(function (access_token) {
                img.access_token = access_token[0];
            });
        }

        return def.then(function () {
            if (!img.isDocument) {
                if (img.access_token && self.options.res_model !== 'ir.ui.view') {
                    img.src += _.str.sprintf('?access_token=%s', img.access_token);
                }
                if (!self.$media.is('img')) {
                    // Note: by default the images receive the bootstrap opt-in
                    // img-fluid class. We cannot make them all responsive
                    // by design because of libraries and client databases img.
                    self.$media = $('<img/>', {class: 'img-fluid o_we_custom_image'});
                    self.media = self.$media[0];
                }
                self.$media.attr('src', img.src);

            } else {
                if (!self.$media.is('a')) {
                    $('.note-control-selection').hide();
                    self.$media = $('<a/>');
                    self.media = self.$media[0];
                }
                var href = '/web/content/' + img.id + '?';
                if (img.access_token && self.options.res_model !== 'ir.ui.view') {
                    href += _.str.sprintf('access_token=%s&', img.access_token);
                }
                href += 'unique=' + img.checksum + '&download=true';
                self.$media.attr('href', href);
                self.$media.addClass('o_image').attr('title', img.name).attr('data-mimetype', img.mimetype);
            }

            self.$media.attr('alt', img.alt);
            var style = self.style;
            if (style) {
                self.$media.css(style);
            }

            // Remove crop related attributes
            if (self.$media.attr('data-aspect-ratio')) {
                var attrs = ['aspect-ratio', 'x', 'y', 'width', 'height', 'rotate', 'scale-x', 'scale-y'];
                _.each(attrs, function (attr) {
                    self.$media.removeData(attr);
                    self.$media.removeAttr('data-' + attr);
                });
            }
            return self.media;
        });
    },
    /**
     * @private
     */
    _toggleImage: function (attachment, clearSearch, forceSelect) {
        if (this.multiImages) {
            var img = _.select(this.selectedImages, function (v) {
                return v.id === attachment.id;
            });
            if (img.length) {
                if (!forceSelect) {
                    this.selectedImages.splice(this.selectedImages.indexOf(img[0]),1);
                }
            } else {
                this.selectedImages.push(attachment);
            }
        } else {
            this.selectedImages = [attachment];
        }
        this._highlightSelectedImages();

        if (clearSearch) {
            this.search('');
        }
    },
    /**
     * Create an attachment for each new file, and then open the Preview dialog
     * for one image at a time.
     *
     * @private
     */
    _uploadImageFiles: function () {
        var self = this;
        var uploadMutex = new concurrency.Mutex();
        var previewMutex = new concurrency.Mutex();
        var defs = [];
        // upload the smallest file first to block the user the least possible
        var files = _.sortBy(this.$fileInput[0].files, 'size');
        for (var file of files) {
            // upload one file at a time
            var defUpload = uploadMutex.exec(function () {
                // TODO SEB apparently the last image of a multi is uploaded in place of all the others
                return self._uploadImageFile(file).then(function (attachment) {
                    // show only one preview at a time
                    previewMutex.exec(function () {
                        return self._previewAttachment(attachment);
                    });
                });
            });
            defs.push(defUpload);
        }

        self.$fileInput.val('');

        var defUploads = $.when.apply($, defs).then(function () {
            // success for all uploads
            self.$uploadButton.addClass('btn-success');
        }).fail(function () {
            // at least one upload failed
            self.$uploadButton.addClass('btn-danger');
            self.$el.find('.form-text').text(
                _("At least one of the files you selected could not be saved.")
            );
        });

        return $.when(defUploads, previewMutex.getUnlockedDef());

        // TODO SEB when all done:
        // if (!self.multiImages) {
        //     self.trigger_up('save_request');
        // }
        // also : this.selectedImages = attachments;
    },
    /**
     * Open the image preview dialog for the given attachment.
     *
     * @private
     */
    _previewAttachment: function (attachment) {
        var def = $.Deferred();
        new ImagePreviewDialog(this, {}, attachment, def).open();
        return def;
    },
    /**
     * Creates an attachment for the given file.
     *
     * @private
     * @param {Blob|File} file
     * @returns {Deferred} resolved with the attachment
     */
    _uploadImageFile: function (file) {
        var self = this;

        return utils.getDataURLFromFile(file).then(function (dataURL) {
            return self._rpc({
                route: '/web_editor/attachment/add_image_base64',
                params: {
                    'res_id': self.options.res_id,
                    'image_base64': dataURL.split(',')[1],
                    'filename': file.name,
                    'res_model': self.options.res_model,
                    'filters': self.firstFilters.join('_'),
                },
            }).progress(function (ev) {
                // TODO SEB make a nice progress bar?
            }).then(function (attachment) {
                self._handleNewAttachment(attachment);
                return attachment;
            });
        });
        // TODO SEB handle error
    },

    _handleNewAttachment: function (attachment) {
        attachment.src = attachment.url || _.str.sprintf('/web/image/%s/%s', attachment.id, encodeURI(attachment.name)); // Name is added for SEO purposes
        attachment.isDocument = !(/gif|jpe|jpg|png/.test(attachment.mimetype));
        this._toggleImage(attachment, true);
    },
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onImageClick: function (ev, force_select) {
        var $img = $(ev.currentTarget);
        var attachment = _.find(this.records, function (record) {
            return record.id === $img.data('id');
        });
        this._toggleImage(attachment, false, force_select);
    },
    /**
     * @private
     */
    _onImageDblClick: function (ev) {
        this._onImageClick(ev, true);
        this.trigger_up('save_request');
    },
    /**
     * Handles change of the file input: create attachments with the new files
     * and open the Preview dialog for each of them. Locks the save button until
     * all new files have been processed.
     *
     * @private
     */
    _onChangeFileInput: function () {
        this.$form.removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');
        this.$formText.empty();
        this.$('.o_upload_media_button').removeClass('btn-danger btn-success');
        return this._mutex.exec(this._uploadImageFiles.bind(this));
    },
    /**
     * @private
     */
    _onRemoveClick: function (ev) {
        var self = this;
        Dialog.confirm(this, _t("Are you sure you want to delete this file ?"), {
            confirm_callback: function () {
                self.$formText.empty();
                var $a = $(ev.currentTarget);
                var id = parseInt($a.data('id'), 10);
                var attachment = _.findWhere(self.records, {id: id});
                 return self._rpc({
                    route: '/web_editor/attachment/remove',
                    params: {
                        ids: [id],
                    },
                }).then(function (prevented) {
                    if (_.isEmpty(prevented)) {
                        self.records = _.without(self.records, attachment);
                        self._renderImages();
                        return;
                    }
                    self.$formText.replaceWith(QWeb.render('wysiwyg.widgets.image.existing.error', {
                        views: prevented[id],
                    }));
                });
            }
        });
    },
    /**
     * @private
     */
    _onInputUrl: function () {
        var inputValue = this.$urlInput.val();
        var emptyValue = (inputValue === '');

        var isURL = /^.+\..+$/.test(inputValue); // TODO improve
        var isImage = _.any(['.gif', '.jpe', '.jpg', '.png'], function (format) {
            return inputValue.endsWith(format);
        });

        this.$addUrlButton.toggleClass('btn-secondary', emptyValue)
            .toggleClass('btn-primary', !emptyValue)
            .prop('disabled', !isURL);
        if (!this.options.document) {
            this.$addUrlButton.text((isURL && !isImage) ? _t("Add as document") : _t("Add image"));
        }
        this.$urlSuccess.toggleClass('d-none', !isURL);
        this.$urlWarning.toggleClass('d-none', !isURL || this.options.document || isImage);
        this.$urlError.toggleClass('d-none', emptyValue || isURL);
    },
    /**
     * @private
     */
    _onUploadButtonClick: function () {
        this.$('input[type=file]').click();
    },
    /**
     * @private
     */
    _onUploadURLButtonClick: function () {
        var self = this;
        return this._rpc({
            route: '/web_editor/attachment/add_url',
            params: {
                'res_id': this.options.res_id,
                'url': this.$urlInput.val(),
                'res_model': this.options.res_model,
                'filters': this.firstFilters.join('_'),
            },
        }).then(function (attachment) {
            self.$urlInput.val('');
            self._handleNewAttachment(attachment);
        });
        // TODO SEB handle error
    },
    /**
     * @private
     */
    _onLoadMoreClick: function () {
        this._loadMoreImages();
    },
    /**
     * @override
     */
    _onSearchInput: function () {
        this.imagesRows = this.IMAGES_ROWS;
        this._super.apply(this, arguments);
    },
});

/**
 * Let users choose a font awesome icon, support all font awesome loaded in the
 * css files.
 */
var IconWidget = MediaWidget.extend({
    template: 'wysiwyg.widgets.font-icons',
    events: _.extend({}, MediaWidget.prototype.events || {}, {
        'click .font-icons-icon': '_onIconClick',
        'dblclick .font-icons-icon': '_onIconDblClick',
    }),

    /**
     * @constructor
     */
    init: function (parent, media) {
        this._super.apply(this, arguments);

        fonts.computeFonts();
        this.iconsParser = fonts.fontIcons;
        this.alias = _.flatten(_.map(this.iconsParser, function (data) {
            return data.alias;
        }));
    },
    /**
     * @override
     */
    start: function () {
        this.$icons = this.$('.font-icons-icon');
        var classes = (this.media && this.media.className || '').split(/\s+/);
        for (var i = 0; i < classes.length; i++) {
            var cls = classes[i];
            if (_.contains(this.alias, cls)) {
                this.selectedIcon = cls;
                this._highlightSelectedIcon();
            }
        }
        this.nonIconClasses = _.without(classes, 'media_iframe_video', this.selectedIcon);

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    save: function () {
        var style = this.$media.attr('style') || '';
        var iconFont = this._getFont(this.selectedIcon) || {base: 'fa', font: ''};
        var finalClasses = _.uniq(this.nonIconClasses.concat([iconFont.base, iconFont.font]));
        if (!this.$media.is('span')) {
            var $span = $('<span/>');
            $span.data(this.$media.data());
            this.$media = $span;
            this.media = this.$media[0];
            style = style.replace(/\s*width:[^;]+/, '');
        }
        this.$media.attr({
            class: _.compact(finalClasses).join(' '),
            style: style || null,
        });
        return this.media;
    },
    /**
     * @override
     */
    search: function (needle) {
        var iconsParser = this.iconsParser;
        if (needle && needle.length) {
            iconsParser = [];
            _.filter(this.iconsParser, function (data) {
                var cssData = _.filter(data.cssData, function (cssData) {
                    return _.find(cssData.names, function (alias) {
                        return alias.indexOf(needle) >= 0;
                    });
                });
                if (cssData.length) {
                    iconsParser.push({
                        base: data.base,
                        cssData: cssData,
                    });
                }
            });
        }
        this.$('div.font-icons-icons').html(
            QWeb.render('wysiwyg.widgets.font-icons.icons', {iconsParser: iconsParser})
        );
        return $.when();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _clear: function () {
        var allFaClasses = /(^|\s)(fa(\s|$)|fa-[^\s]*)/g;
        this.media.className = this.media.className && this.media.className.replace(allFaClasses, ' ');
    },
    /**
     * @private
     */
    _getFont: function (classNames) {
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
                        parser: fontIcon.parser,
                        font: cssData.names[0],
                    };
                }
            }
        }
        return null;
    },
    /**
     * @private
     */
    _highlightSelectedIcon: function () {
        var self = this;
        this.$icons.removeClass('o_selected');
        this.$icons.filter(function (i, el) {
            return _.contains($(el).data('alias').split(','), self.selectedIcon);
        }).addClass('o_selected');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onIconClick: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();

        this.selectedIcon = $(ev.currentTarget).data('id');
        this._highlightSelectedIcon();
    },
    /**
     * @private
     */
    _onIconDblClick: function () {
        this.trigger_up('save_request');
    },
});

/**
 * Let users choose a video, support all summernote video, and embed iframe.
 */
var VideoWidget = MediaWidget.extend({
    template: 'wysiwyg.widgets.video',
    events: _.extend({}, MediaWidget.prototype.events || {}, {
        'change .o_video_dialog_options input': '_onUpdateVideoOption',
        'input textarea#o_video_text': '_onVideoCodeInput',
        'change textarea#o_video_text': '_onVideoCodeChange',
    }),

    /**
     * @constructor
     */
    init: function (parent, media) {
        this._super.apply(this, arguments);
        this._onVideoCodeInput = _.debounce(this._onVideoCodeInput, 1000);
    },
    /**
     * @override
     */
    start: function () {
        this.$content = this.$('.o_video_dialog_iframe');

        if (this.media) {
            var $media = $(this.media);
            var src = $media.data('oe-expression') || $media.data('src') || '';
            this.$('textarea#o_video_text').val(src);

            this.$('input#o_video_autoplay').prop('checked', src.indexOf('autoplay=1') >= 0);
            this.$('input#o_video_hide_controls').prop('checked', src.indexOf('controls=0') >= 0);
            this.$('input#o_video_loop').prop('checked', src.indexOf('loop=1') >= 0);
            this.$('input#o_video_hide_fullscreen').prop('checked', src.indexOf('fs=0') >= 0);
            this.$('input#o_video_hide_yt_logo').prop('checked', src.indexOf('modestbranding=1') >= 0);
            this.$('input#o_video_hide_dm_logo').prop('checked', src.indexOf('ui-logo=0') >= 0);
            this.$('input#o_video_hide_dm_share').prop('checked', src.indexOf('sharing-enable=0') >= 0);

            this._updateVideo();
        }

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    save: function () {
        this._updateVideo();
        if (this.$('.o_video_dialog_iframe').is('iframe')) {
            this.$media = $(
                '<div class="media_iframe_video" data-oe-expression="' + this.$content.attr('src') + '">' +
                    '<div class="css_editable_mode_display">&nbsp;</div>' +
                    '<div class="media_iframe_video_size" contenteditable="false">&nbsp;</div>' +
                    '<iframe src="' + this.$content.attr('src') + '" frameborder="0" contenteditable="false"></iframe>' +
                '</div>'
            );
            this.media = this.$media[0];
        }
        return this.media;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _clear: function () {
        if (this.media.dataset.src) {
            try {
                delete this.media.dataset.src;
            } catch (e) {
                this.media.dataset.src = undefined;
            }
        }
        var allVideoClasses = /(^|\s)media_iframe_video(\s|$)/g;
        this.media.className = this.media.className && this.media.className.replace(allVideoClasses, ' ');
        this.media.innerHTML = '';
    },
    /**
     * Creates a video node according to the given URL and options. If not
     * possible, returns an error code.
     *
     * @private
     * @param {string} url
     * @param {Object} options
     * @returns {Object}
     *          $video -> the created video jQuery node
     *          type -> the type of the created video
     *          errorCode -> if defined, either '0' for invalid URL or '1' for
     *              unsupported video provider
     */
    _createVideoNode: function (url, options) {
        options = options || {};

        // Video url patterns(youtube, instagram, vimeo, dailymotion, youku, ...)
        var ytRegExp = /^(?:(?:https?:)?\/\/)?(?:www\.)?(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))((\w|-){11})(?:\S+)?$/;
        var ytMatch = url.match(ytRegExp);

        var insRegExp = /(.*)instagram.com\/p\/(.[a-zA-Z0-9]*)/;
        var insMatch = url.match(insRegExp);

        var vinRegExp = /\/\/vine.co\/v\/(.[a-zA-Z0-9]*)/;
        var vinMatch = url.match(vinRegExp);

        var vimRegExp = /\/\/(player.)?vimeo.com\/([a-z]*\/)*([0-9]{6,11})[?]?.*/;
        var vimMatch = url.match(vimRegExp);

        var dmRegExp = /.+dailymotion.com\/(video|hub|embed)\/([^_]+)[^#]*(#video=([^_&]+))?/;
        var dmMatch = url.match(dmRegExp);

        var ykuRegExp = /(.*).youku\.com\/(v_show\/id_|embed\/)(.+)/;
        var ykuMatch = url.match(ykuRegExp);

        var $video = $('<iframe>').width(1280).height(720).attr('frameborder', 0).addClass('o_video_dialog_iframe');
        var videoType = 'yt';

        if (!/^(http:\/\/|https:\/\/|\/\/)[a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,5}(:[0-9]{1,5})?(\/.*)?$/i.test(url)){
            return {errorCode: 0};
        }

        var autoplay = options.autoplay ? '?autoplay=1' : '?autoplay=0';

        if (ytMatch && ytMatch[1].length === 11) {
            $video.attr('src', '//www.youtube.com/embed/' + ytMatch[1] + autoplay);
        } else if (insMatch && insMatch[2].length) {
            $video.attr('src', '//www.instagram.com/p/' + insMatch[2] + '/embed/');
            videoType = 'ins';
        } else if (vinMatch && vinMatch[0].length) {
            $video.attr('src', vinMatch[0] + '/embed/simple');
            videoType = 'vin';
        } else if (vimMatch && vimMatch[3].length) {
            $video.attr('src', '//player.vimeo.com/video/' + vimMatch[3] + autoplay);
            videoType = 'vim';
        } else if (dmMatch && dmMatch[2].length) {
            var justId = dmMatch[2].replace('video/', '');
            $video.attr('src', '//www.dailymotion.com/embed/video/' + justId + autoplay);
            videoType = 'dm';
        } else if (ykuMatch && ykuMatch[3].length) {
            var ykuId = ykuMatch[3].indexOf('.html?') >= 0 ? ykuMatch[3].substring(0, ykuMatch[3].indexOf('.html?')) : ykuMatch[3];
            $video.attr('src', '//player.youku.com/embed/' + ykuId);
            videoType = 'yku';
        } else {
            return {errorCode: 1};
        }

        if (ytMatch) {
            $video.attr('src', $video.attr('src') + '&rel=0');
        }
        if (options.loop && (ytMatch || vimMatch)) {
            $video.attr('src', $video.attr('src') + '&loop=1');
        }
        if (options.hide_controls && (ytMatch || dmMatch)) {
            $video.attr('src', $video.attr('src') + '&controls=0');
        }
        if (options.hide_fullscreen && ytMatch) {
            $video.attr('src', $video.attr('src') + '&fs=0');
        }
        if (options.hide_yt_logo && ytMatch) {
            $video.attr('src', $video.attr('src') + '&modestbranding=1');
        }
        if (options.hide_dm_logo && dmMatch) {
            $video.attr('src', $video.attr('src') + '&ui-logo=0');
        }
        if (options.hide_dm_share && dmMatch) {
            $video.attr('src', $video.attr('src') + '&sharing-enable=0');
        }

        return {$video: $video, type: videoType};
    },
    /**
     * Updates the video preview according to video code and enabled options.
     *
     * @private
     */
    _updateVideo: function () {
        // Reset the feedback
        this.$content.empty();
        this.$('#o_video_form_group').removeClass('o_has_error o_has_success').find('.form-control, .custom-select').removeClass('is-invalid is-valid');
        this.$('.o_video_dialog_options div').addClass('d-none');

        // Check video code
        var $textarea = this.$('textarea#o_video_text');
        var code = $textarea.val().trim();
        if (!code) {
            return;
        }

        // Detect if we have an embed code rather than an URL
        var embedMatch = code.match(/(src|href)=["']?([^"']+)?/);
        if (embedMatch && embedMatch[2].length > 0 && embedMatch[2].indexOf('instagram')) {
            embedMatch[1] = embedMatch[2]; // Instagram embed code is different
        }
        var url = embedMatch ? embedMatch[1] : code;

        var query = this._createVideoNode(url, {
            autoplay: this.$('input#o_video_autoplay').is(':checked'),
            hide_controls: this.$('input#o_video_hide_controls').is(':checked'),
            loop: this.$('input#o_video_loop').is(':checked'),
            hide_fullscreen: this.$('input#o_video_hide_fullscreen').is(':checked'),
            hide_yt_logo: this.$('input#o_video_hide_yt_logo').is(':checked'),
            hide_dm_logo: this.$('input#o_video_hide_dm_logo').is(':checked'),
            hide_dm_share: this.$('input#o_video_hide_dm_share').is(':checked'),
        });

        var $optBox = this.$('.o_video_dialog_options');

        // Show / Hide preview elements
        this.$el.find('.o_video_dialog_preview_text, .media_iframe_video_size').add($optBox).toggleClass('d-none', !query.$video);
        // Toggle validation classes
        this.$el.find('#o_video_form_group')
            .toggleClass('o_has_error', !query.$video).find('.form-control, .custom-select').toggleClass('is-invalid', !query.$video)
            .end()
            .toggleClass('o_has_success', !!query.$video).find('.form-control, .custom-select').toggleClass('is-valid', !!query.$video);

        // Individually show / hide options base on the video provider
        $optBox.find('div.o_' + query.type + '_option').removeClass('d-none');

        // Hide the entire options box if no options are available
        $optBox.toggleClass('d-none', $optBox.find('div:not(.d-none)').length === 0);

        if (query.type === 'yt') {
            // Youtube only: If 'hide controls' is checked, hide 'fullscreen'
            // and 'youtube logo' options too
            this.$('input#o_video_hide_fullscreen, input#o_video_hide_yt_logo').closest('div').toggleClass('d-none', this.$('input#o_video_hide_controls').is(':checked'));
        }

        var $content = query.$video;
        if (!$content) {
            switch (query.errorCode) {
                case 0:
                    $content = $('<div/>', {
                        class: 'alert alert-danger o_video_dialog_iframe mb-2 mt-2',
                        text: _t("The provided url is not valid"),
                    });
                    break;
                case 1:
                    $content = $('<div/>', {
                        class: 'alert alert-warning o_video_dialog_iframe mb-2 mt-2',
                        text: _t("The provided url does not reference any supported video"),
                    });
                    break;
            }
        }
        this.$content.replaceWith($content);
        this.$content = $content;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when a video option changes -> Updates the video preview.
     *
     * @private
     */
    _onUpdateVideoOption: function () {
        this._updateVideo();
    },
    /**
     * Called when the video code (URL / Iframe) change is confirmed -> Updates
     * the video preview immediately.
     *
     * @private
     */
    _onVideoCodeChange: function () {
        this._updateVideo();
    },
    /**
     * Called when the video code (URL / Iframe) changes -> Updates the video
     * preview (note: this function is automatically debounced).
     *
     * @private
     */
    _onVideoCodeInput: function () {
        this._updateVideo();
    },
});

return {
    MediaWidget: MediaWidget,
    ImageWidget: ImageWidget,
    IconWidget: IconWidget,
    VideoWidget: VideoWidget,
};
});
