odoo.define('product.generate_pricelist', function (require) {
'use strict';

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var FieldMany2One = require('web.relational_fields').FieldMany2One;
var StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

var QtyTagWidget = Widget.extend({
    template: 'product.report_pricelist_qty',
    events: {
        'click .o_add_qty': '_onClickAddQty',
        'click .o_remove_qty': '_onClickRemoveQty',
    },
    /**
     * @override
     */
    init: function (parent, defaulQuantities) {
        this._super.apply(this, arguments);
        this.quantities = defaulQuantities;
        this.MAX_QTY = 5;
    },

    //--------------------------------------------------------------------------
    // private
    //--------------------------------------------------------------------------

    /**
     * Render quantity badges.
     *
     * @private
     */
    _render: function () {
        this.$('.o_badges').empty();
        this.quantities = this.quantities.sort((a, b) => a - b);
        $(QWeb.render('product.report_pricelist_qty_badges', {quantities: this.quantities})).appendTo(this.$('.o_badges'));
        this.$('.o_product_qty').focus();
        this.trigger_up('qty_changed', {quantities: this.quantities});
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Add a quantity when add(+) button clicked.
     * 
     * @private
     */
    _onClickAddQty: function () {
        if (this.quantities.length >= this.MAX_QTY) {
            this.do_notify(_.str.sprintf(_t("Maximum %d quantities can be added."), this.MAX_QTY));
            return;
        }
        const qty = parseInt(this.$('.o_product_qty').val());
        if (qty && qty > 0) {
            // Check qty already exist
            if (this.quantities.indexOf(qty) === -1) {
                this.quantities.push(qty);
                this._render();
            } else {
                this.do_notify(_.str.sprintf(_t("Already %d quantity exist."), qty));
            }
        } else {
            this.do_notify(_t("Add a correct quantity."));
        }
    },
    /**
     * Remove quantity.
     *
     * @private
     * @param {jQueryEvent} ev
     */
    _onClickRemoveQty: function (ev) {
        const qty = parseInt($(ev.currentTarget).closest('.badge').data('qty'));
        this.quantities = this.quantities.filter(q => q !== qty);
        this._render();
    },
});

var GeneratePriceList = AbstractAction.extend(StandaloneFieldManagerMixin, {
    hasControlPanel: true,
    events: {
        'click .o_action': '_onClickAction',
    },
    custom_events: {
        ...StandaloneFieldManagerMixin.custom_events,
        field_changed: '_onFieldChanged',
        qty_changed: '_onQtyChanged',
    },
    /**
     * @override
     */
    init: function (parent, params) {
        this._super.apply(this, arguments);
        StandaloneFieldManagerMixin.init.call(this);
        this.context = params.context;
        this.context.quantities = [1, 5, 10];
    },
    /**
     * @override
     */
    willStart: function () {
        const prom = this.model.makeRecord('report.product.report_pricelist', [{
            name: 'pricelist',
            type: 'many2one',
            relation: 'product.pricelist',
            value: this.context.default_pricelist,
        }]).then(recordID => {
            const record = this.model.get(recordID);
            this.many2one = new FieldMany2One(this, 'pricelist', record, {
                mode: 'edit',
                attrs: {
                    can_create: false,
                    can_write: false,
                    options: {no_open: true},
                },
            });
            this._registerWidget(recordID, 'pricelist', this.many2one);
        });
        return Promise.all([prom, this._getHtml(), this._super.apply(this, arguments)]);
    },
    /**
     * @override
     */
    start: function () {
        return this._super.apply(this, arguments).then(() => {
            this._renderComponent();
            this.update_cp();
            this.$('.o_content').html(this.reportHtml);
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    update_cp: function () {
        this.updateControlPanel({
            cp_content: {
                $buttons: this.$buttonPrint,
                $searchview_buttons: this.$searchView,
            },
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Get template to display report.
     *
     * @private
     * @returns {Promise}
     */
    _getHtml: function () {
        return this._rpc({
            model: 'report.product.report_pricelist',
            method: 'get_html',
            context: this.context,
        }).then(result => {
            this.reportHtml = result;
        });
    },
    /**
     * Reload report.
     *
     * @private
     * @returns {Promise}
     */
    _reload: function () {
        return this._getHtml().then(() => {
            this.$('.o_content').html(this.reportHtml);
        });
    },
    /**
     * Render search view and print button.
     *
     * @private
     */
    _renderComponent: function () {
        this.$buttonPrint = $('<button>', {
            class: 'btn btn-primary',
            text: _t("Print"),
        }).on('click', this._onClickPrint.bind(this));

        this.$searchView = $(QWeb.render('product.report_pricelist_search'));
        this.many2one.appendTo(this.$searchView.find('.o_pricelist'));

        const qtyTagWidget = new QtyTagWidget(this, this.context.quantities);
        qtyTagWidget.appendTo(this.$searchView.find('.o_product_qty'));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Open form view of particular record when link clicked.
     *
     * @private
     * @param {jQueryEvent} ev
     */
    _onClickAction: function (ev) {
        ev.preventDefault();
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: $(ev.currentTarget).data('model'),
            res_id: $(ev.currentTarget).data('res-id'),
            views: [[false, 'form']],
            target: 'new',
        });
    },
    /**
     * Print report in PDF when button clicked.
     *
     * @private
     */
    _onClickPrint: function () {
        const reportName = _.str.sprintf('product.report_pricelist?active_model=%s&active_ids=%s&pricelist_id=%s&quantities=%s',
            this.context.active_model,
            this.context.active_ids,
            this.context.pricelist_id || '',
            this.context.quantities.toString() || '1',
        );
        this.do_action({
            type: 'ir.actions.report',
            report_type: 'qweb-pdf',
            report_name: reportName,
            report_file: 'product.report_pricelist',
        });
    },
    /**
     * Reload report when pricelist changed.
     *
     * @override
     */
    _onFieldChanged: function (event) {
        this.context.pricelist_id = event.data.changes.pricelist.id;
        StandaloneFieldManagerMixin._onFieldChanged.apply(this, arguments);
        this._reload();
    },
    /**
     * Reload report when quantities changed.
     *
     * @private
     * @param {OdooEvent} ev
     * @param {integer[]} event.data.quantities
     */
    _onQtyChanged: function (ev) {
        this.context.quantities = ev.data.quantities;
        this._reload();
    },
});

core.action_registry.add('generate_pricelist', GeneratePriceList);

return GeneratePriceList;

});
