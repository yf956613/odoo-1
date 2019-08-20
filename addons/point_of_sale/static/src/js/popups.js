odoo.define('point_of_sale.popups', function (require) {
"use strict";

// This file contains the Popups.
// Popups must be loaded and named in chrome.js. 
// They are instanciated / destroyed with the .gui.show_popup()
// and .gui.close_popup() methods.

var PosBaseWidget = require('point_of_sale.BaseWidget');
var gui = require('point_of_sale.gui');
var rpc = require('web.rpc');
var _t  = require('web.core')._t;


var PopupWidget = PosBaseWidget.extend({
    template: 'PopupWidget',
    init: function(parent, args) {
        this._super(parent, args);
        this.options = {};
    },
    events: {
        'click .button.cancel':  'click_cancel',
        'click .button.confirm': 'click_confirm',
        'click .selection-item': 'click_item',
        'click .input-button':   'click_numpad',
        'click .mode-button':    'click_numpad',
    },

    // show the popup !  
    show: function(options){
        if(this.$el){
            this.$el.removeClass('oe_hidden');
        }
        
        if (typeof options === 'string') {
            this.options = {title: options};
        } else {
            this.options = options || {};
        }

        this.renderElement();

        // popups block the barcode reader ... 
        if (this.pos.barcode_reader) {
            this.pos.barcode_reader.save_callbacks();
            this.pos.barcode_reader.reset_action_callbacks();
        }
    },

    // called before hide, when a popup is closed.
    // extend this if you want a custom action when the 
    // popup is closed.
    close: function(){
        if (this.pos.barcode_reader) {
            this.pos.barcode_reader.restore_callbacks();
        }
    },

    // hides the popup. keep in mind that this is called in 
    // the initialization pass of the pos instantiation, 
    // so you don't want to do anything fancy in here
    hide: function(){
        if (this.$el) {
            this.$el.addClass('oe_hidden');
        }
    },

    // what happens when we click cancel
    // ( it should close the popup and do nothing )
    click_cancel: function(){
        this.gui.close_popup();
        if (this.options.cancel) {
            this.options.cancel.call(this);
        }
    },

    // what happens when we confirm the action
    click_confirm: function(){
        this.gui.close_popup();
        if (this.options.confirm) {
            this.options.confirm.call(this);
        }
    },

    // Since Widget does not support extending the events declaration
    // we declared them all in the top class.
    click_item: function(){},
    click_numad: function(){},
});
gui.define_popup({name:'alert', widget: PopupWidget});

var ErrorPopupWidget = PopupWidget.extend({
    template:'ErrorPopupWidget',
    show: function(options){
        this._super(options);
        this.gui.play_sound('error');
    },
});
gui.define_popup({name:'error', widget: ErrorPopupWidget});


var SyncErrorPopupWidget = ErrorPopupWidget.extend({
    template:'SyncErrorPopupWidget',
    show: function(opts) {
        var self = this;
        this._super(opts);

        this.$('.stop_showing_sync_errors').off('click').click(function(){
            self.gui.show_sync_errors = false;
            self.click_confirm();
        });
    }
});
gui.define_popup({name:'error-sync', widget: SyncErrorPopupWidget});


var ErrorTracebackPopupWidget = ErrorPopupWidget.extend({
    template:'ErrorTracebackPopupWidget',
    show: function(opts) {
        var self = this;
        this._super(opts);

        this.$('.download').off('click').click(function(){
            self.gui.prepare_download_link(self.options.body,
                _t('error') + ' ' + moment().format('YYYY-MM-DD-HH-mm-ss') + '.txt',
                '.download', '.download_error_file');
        });

        this.$('.email').off('click').click(function(){
            self.gui.send_email( self.pos.company.email,
                _t('IMPORTANT: Bug Report From Odoo Point Of Sale'),
                self.options.body);
        });
    }
});
gui.define_popup({name:'error-traceback', widget: ErrorTracebackPopupWidget});


var ErrorBarcodePopupWidget = ErrorPopupWidget.extend({
    template:'ErrorBarcodePopupWidget',
    show: function(barcode){
        this._super({barcode: barcode});
    },
});
gui.define_popup({name:'error-barcode', widget: ErrorBarcodePopupWidget});


var ConfirmPopupWidget = PopupWidget.extend({
    template: 'ConfirmPopupWidget',
});
gui.define_popup({name:'confirm', widget: ConfirmPopupWidget});

/**
 * A popup that allows the user to select one item from a list.
 *
 * Example::
 *
 *    show_popup('selection',{
 *        title: "Popup Title",
 *        list: [
 *            { label: 'foobar',  item: 45 },
 *            { label: 'bar foo', item: 'stuff' },
 *        ],
 *        confirm: function(item) {
 *            // get the item selected by the user.
 *        },
 *        cancel: function(){
 *            // user chose nothing
 *        }
 *    });
 */

var SelectionPopupWidget = PopupWidget.extend({
    template: 'SelectionPopupWidget',
    show: function(options){
        var self = this;
        options = options || {};
        this._super(options);

        this.list = options.list || [];
        this.is_selected = options.is_selected || function (item) { return false; };
        this.renderElement();
    },
    click_item : function(event) {
        this.gui.close_popup();
        if (this.options.confirm) {
            var item = this.list[parseInt($(event.target).data('item-index'))];
            item = item ? item.item : item;
            this.options.confirm.call(self,item);
        }
    }
});
gui.define_popup({name:'selection', widget: SelectionPopupWidget});


var TextInputPopupWidget = PopupWidget.extend({
    template: 'TextInputPopupWidget',
    show: function(options){
        options = options || {};
        this._super(options);

        this.renderElement();
        this.$('input,textarea').focus();
    },
    click_confirm: function(){
        var value = this.$('input,textarea').val();
        this.gui.close_popup();
        if( this.options.confirm ){
            this.options.confirm.call(this,value);
        }
    },
});
gui.define_popup({name:'textinput', widget: TextInputPopupWidget});


var TextAreaPopupWidget = TextInputPopupWidget.extend({
    template: 'TextAreaPopupWidget',
});
gui.define_popup({name:'textarea', widget: TextAreaPopupWidget});

var PackLotLinePopupWidget = PopupWidget.extend({
    template: 'PackLotLinePopupWidget',
    events: _.extend({}, PopupWidget.prototype.events, {
        'click .remove-lot': 'remove_lot',
        'click .ignore-lot':  'click_ignore',
        'keydown': 'add_lot',
        'blur .packlot-line-input': 'lose_input_focus'
    }),

    show: function(options){
        this._super(options);
        this.focus();
    },

    click_confirm: function(){
        var self = this;
        var lots = [];
        var pack_lot_lines = this.options.pack_lot_lines;
        var existing_lots = this.options.order.get_existing_lots();
        this.lot_errors = {};
        this.$('.packlot-line-input').each(function(index, el) {
            var cid = $(el).attr('cid'),
                lot_name = $(el).val();
            var pack_line = pack_lot_lines.get({cid: cid});
            pack_line.set_lot_name(lot_name);
            lots.push(lot_name);
        });
        rpc.query({
            model: "product.product",
            method: "get_lots_quantity",
            args: [pack_lot_lines.order_line.product.id, lots],
        }).then(function (result) {
            var tracking_type = self.options.order_line.product.tracking;
            var line_qty = self.options.order_line.quantity;

            pack_lot_lines.forEach(function(lot) {
                var lot_name = lot.get('lot_name');
                if (!lot_name) return;

                var available_qty = result[lot_name];
                var existing_qty = existing_lots[lot_name];
                var lot_quantity = self.pos.db.load("lot_quantity", {});
                lot_quantity[lot_name] = available_qty;
                self.pos.db.save("lot_quantity", lot_quantity);

                if (tracking_type == 'lot') {
                    if (!result.hasOwnProperty(lot_name)) {
                        self.lot_errors[lot.cid] = _("This lot could not be found.");
                    } else if (available_qty <= 0) {
                        self.lot_errors[lot.cid] = _("This lot has no available quantity.");
                    } else if (available_qty < line_qty) {
                        self.lot_errors[lot.cid] = _("This lot has a too low available quantity.");
                    } else if (available_qty - existing_qty < line_qty) {
                        self.lot_errors[lot.cid] = _("This lot is already added and it has a too low available quantity");
                    }
                }
                if (tracking_type == 'serial') {
                    if (!result.hasOwnProperty(lot_name)) {
                        self.lot_errors[lot.cid] = _("This serial could not be found.");
                    } else if (available_qty <= 0) {
                        self.lot_errors[lot.cid] = _("Product with this serial is already sold.");
                    } else if (available_qty - existing_qty < line_qty) {
                        self.lot_errors[lot.cid] = _("This serial is already added in the order");
                    }
                }
            });
            if (_.isEmpty(self.lot_errors) ) {
                self.process_lots();
            } else {
                self.renderElement();
                self.focus();
            }
        }).guardedCatch(this.process_lots.bind(this));

    },
    click_ignore: function () {
        this.process_lots();
    },
    process_lots: function () {
        this.options.pack_lot_lines.remove_empty_model();
        this.options.pack_lot_lines.set_quantity_by_lot();
        this.options.order.save_to_db();
        this.options.order_line.trigger('change', this.options.order_line);
        this.gui.close_popup();
    },

    add_lot: function(ev) {
        var $input = $(ev.target);
        var cid = $input.attr('cid');
        if (ev.keyCode === $.ui.keyCode.ENTER && this.options.order_line.product.tracking == 'serial'){
            var pack_lot_lines = this.options.pack_lot_lines,
                lot_name = $input.val();

            var lot_model = pack_lot_lines.get({cid: cid});
            lot_model.set_lot_name(lot_name);  // First set current model then add new one
            if(!pack_lot_lines.get_empty_model()){
                var new_lot_model = lot_model.add();
                this.focus_model = new_lot_model;
            }
            pack_lot_lines.set_quantity_by_lot();
            this.renderElement();
            this.focus();
        }
        var error_class = _.str.sprintf('.lot_warning[cid="%s"]', cid);
        this.$(error_class).remove();
        this.$('.confirm').removeClass('oe_hidden');
        this.$('.warning').addClass('oe_hidden');
    },

    remove_lot: function(ev){
        var pack_lot_lines = this.options.pack_lot_lines,
            $input = $(ev.target).prev(),
            cid = $input.attr('cid');
        var lot_model = pack_lot_lines.get({cid: cid});
        lot_model.remove();
        pack_lot_lines.set_quantity_by_lot();
        this.renderElement();
    },

    lose_input_focus: function(ev){
        var $input = $(ev.target),
            cid = $input.attr('cid');
        var lot_model = this.options.pack_lot_lines.get({cid: cid});
        lot_model.set_lot_name($input.val());
    },

    focus: function(){
        this.$("input[autofocus]").focus();
        this.focus_model = false;   // after focus clear focus_model on widget
    }
});
gui.define_popup({name:'packlotline', widget:PackLotLinePopupWidget});

var NumberPopupWidget = PopupWidget.extend({
    template: 'NumberPopupWidget',
    show: function(options){
        options = options || {};
        this._super(options);

        this.inputbuffer = '' + (options.value   || '');
        this.decimal_separator = _t.database.parameters.decimal_point;
        this.renderElement();
        this.firstinput = true;
    },
    click_numpad: function(event){
        var newbuf = this.gui.numpad_input(
            this.inputbuffer, 
            $(event.target).data('action'), 
            {'firstinput': this.firstinput});

        this.firstinput = (newbuf.length === 0);
        
        if (newbuf !== this.inputbuffer) {
            this.inputbuffer = newbuf;
            this.$('.value').text(this.inputbuffer);
        }
    },
    click_confirm: function(){
        this.gui.close_popup();
        if( this.options.confirm ){
            this.options.confirm.call(this,this.inputbuffer);
        }
    },
});
gui.define_popup({name:'number', widget: NumberPopupWidget});

var PasswordPopupWidget = NumberPopupWidget.extend({
    renderElement: function(){
        this._super();
        this.$('.popup').addClass('popup-password');
    },
    click_numpad: function(event){
        this._super.apply(this, arguments);
        var $value = this.$('.value');
        $value.text($value.text().replace(/./g, '•'));
    },
});
gui.define_popup({name:'password', widget: PasswordPopupWidget});

var OrderImportPopupWidget = PopupWidget.extend({
    template: 'OrderImportPopupWidget',
});
gui.define_popup({name:'orderimport', widget: OrderImportPopupWidget});

return PopupWidget;
});
