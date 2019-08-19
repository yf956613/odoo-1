odoo.define('mrp.MrpDocumentsKanbanController', function (require) {
"use strict";

var DocumentViewer = require('mrp.MrpDocumentViewer');
var DocumentsProgressBar = require('mrp.ProgressBar');
var DocumentsProgressCard = require('mrp.ProgressCard');

var KanbanController = require('web.KanbanController');
var utils = require('web.utils');
var core = require('web.core');
var qweb = core.qweb;
var _t = core._t;

var MrpDocumentsKanbanController = KanbanController.extend({
    events: _.extend({}, KanbanController.prototype.events, {
        'change input.o_input_file': '_onMrpAttachmentChange',
        'click .o_mrp_documents_kanban_upload': '_onUpload',
    }),
    custom_events: _.extend({}, KanbanController.prototype.custom_events, {
        kanban_image_clicked: '_onKanbanPreview',
        progress_bar_abort: '_onProgressBarAbort',
    }),
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        const state = this.model.get(this.handle, {raw: true});
        this.uploads = {};
    },
    /**
     * @override
     * @param {jQueryElement} $node
     */
    renderButtons: function ($node) {
        this.$buttons = $(qweb.render('MrpDocumentsKanbanView.buttons'));
        this.$buttons.appendTo($node);
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {integer} ev.data.recordID
     * @param {Array<Object>} ev.data.recordList
     */
    _onKanbanPreview: function (ev) {
        var documents = ev.data.recordList;
        var documentID = ev.data.recordID;
        var documentViewer = new DocumentViewer(this, documents, documentID);
        documentViewer.appendTo(this.$('.o_mrp_documents_kanban_view'));
    },
    /**
     * @private
     */
    _onUpload: function () {
        var self = this;
        var $uploadInput = $('<input>', {type: 'file', name: 'files[]', multiple: 'multiple'});
        var always = function () {
            $uploadInput.remove();
        };
        $uploadInput.on('change', function (ev) {
            self._processFiles(ev.target.files).then(always).guardedCatch(always);
        });
        $uploadInput.click();
    },
    /**
     * Prepares and upload files.
     *
     * @private
     * @param {Object[]} files
     * @returns {Promise}
     */
    _processFiles: function (files) {
        const uploadID = _.uniqueId('uploadID');
        const data = new FormData();

        data.append('csrf_token', core.csrf_token);
        for (const file of files) {
            data.append('ufile', file);
            data.append('default_res_id', this.initialState.context.default_res_id);
            data.append('default_res_model', this.initialState.context.default_res_model);
        }
        let title = files.length + ' Files';
        let type;
        if (files.length === 1) {
            title = files[0].name;
            type = files[0].type;
        }
        const prom = new Promise(resolve => {
            const xhr = new window.XMLHttpRequest();
            xhr.open('POST', '/mrp/upload_attachment');
            this._makeNewProgress(uploadID, xhr, title, type);
            const progressPromise = this._attachProgressBars();
            xhr.onload = async () => {
                await progressPromise;
                resolve();
                const result = JSON.parse(xhr.response);
                if (result.error) {
                    this.do_notify(_t("Error"), result.error, true);
                }
                this._removeProgressBar(uploadID);
            };
            xhr.onerror = async () => {
                await progressPromise;
                resolve();
                this.do_notify(xhr.status, _.str.sprintf(_t('message: %s'), xhr.reponseText), true);
                this._removeProgressBar(uploadID);
            };
            xhr.send(data);
        });
        return prom;
    },
    async _attachProgressBars() {
        for (const upload of Object.values(this.uploads)) {
            if (!upload.folderID) {
                let $targetCard;
                if (upload.progressCard) {
                    await upload.progressCard.prependTo(this.$('.o_mrp_documents_kanban_view'));
                    $targetCard = upload.progressCard.$el;
                }
                await upload.progressBar.appendTo($targetCard);
            }
        }
    },
    /**
     *
     * @private
     * @param {integer} uploadID
     * @returns {Promise}
     */
    async _removeProgressBar(uploadID) {
        const upload = this.uploads[uploadID];
        upload.progressCard && upload.progressCard.destroy();
        upload.progressBar.destroy();
        delete this.uploads[uploadID];
        await this.reload();
    },
    /**
     * Creates a progress bar and a progress card and add them to the uploads.
     *
     * @private
     * @param {integer} uploadID
     * @param {integer} folderID
     * @param {XMLHttpRequest} xhr
     * @param {String} title title of the new progress bar (usually the name of the file).
     * @param {String} type content_type/mimeType of the file
     */
    _makeNewProgress(uploadID, xhr, title, type) {
        const progressCard = new DocumentsProgressCard(this, {
            title,
            type,
        });
        const progressBar = new DocumentsProgressBar(this, {
            xhr,
            title,
            uploadID,
        });
        xhr.upload.addEventListener("progress", ev => {
            if (ev.lengthComputable) {
                progressCard.update(ev.loaded, ev.total);
                progressBar.update(ev.loaded, ev.total);
            }
        });
        this.uploads[uploadID] = {
            progressBar,
            progressCard,
        };
    },
    _onProgressBarAbort(ev) {
        const uploadID = ev.data.uploadID;
        this._removeProgressBar(uploadID);
    },
});

return MrpDocumentsKanbanController;

});
