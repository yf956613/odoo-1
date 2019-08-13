odoo.define('pos_discount.pos_discount', function (require) {
"use strict";

var core = require('web.core');
var screens = require('point_of_sale.screens');
var models = require('point_of_sale.models');

var _t = core._t;

models.load_models({
    model: 'product.product',
    fields: ['display_name', 'lst_price', 'standard_price', 'categ_id', 'pos_categ_id', 'taxes_id',
             'barcode', 'default_code', 'to_weight', 'uom_id', 'description_sale', 'description',
             'product_tmpl_id','tracking'],
    domain: function(self){
        return [['id', '=', self.config.discount_product_id[0]]];
    },
    loaded: function(self, discount_product){
        self.global_discount_product = new models.Product({}, discount_product[0]);
    },
});

var _super_orderline = models.Orderline.prototype;
models.Orderline = models.Orderline.extend({
    initialize: function(attr, options) {
        _super_orderline.initialize.call(this, attr, options);
        var id = options.json ? options.json.id : options.product.id;
        if (id !== options.pos.global_discount_product.id) {
            this.listenTo(this, 'change', function(){
                var order = this.order;
                if (order.global_discount) {
                    order.recompute_global_discount();
                }
            });
        }
    },
    set_product: function(id) {
        if (id !== this.pos.global_discount_product.id){
            _super_orderline.set_product.call(this, id);
        } else {
            this.product = this.pos.global_discount_product; 
        }
    },
});

var _super_order = models.Order.prototype;
models.Order = models.Order.extend({
    export_as_JSON: function() {
        var json = _super_order.export_as_JSON.call(this);
        json.global_discount = this.global_discount;
        return json;
    },
    init_from_JSON: function(json) {
        _super_order.init_from_JSON.call(this, json);
        this.global_discount = json.global_discount || false;
        this.set_global_discount(this.global_discount)
    },
    add_global_discount_lines: function() {
        var self = this;
        var product  = this.pos.global_discount_product;
        if (product === undefined) {
            this.gui.show_popup('error', {
                title : _t("No discount product found"),
                body  : _t("The discount product seems misconfigured."),
            });
            return;
        }
        var grp = {}
        var lines    = this.get_orderlines();
        lines.forEach(function(line){
            var key = line.product.taxes_id || "-1"
            grp[key] = (grp[key] || 0) + line.get_price_without_tax();
        });

        // Add discount
        // We add the price as manually set to avoid recomputation when changing customer.
        Object.keys(grp).forEach(function(key){
            var discount = - self.global_discount / 100 * grp[key];
            if (discount < 0 || discount > 0) {
                var prod = $.extend(true, {}, product);
                if (key == "") {
                    prod.taxes_id = [];
                } else {
                    prod.taxes_id = key.split(',').map(Number);
                }

                self.add_product(prod, {
                    price: discount,
                    extras: {
                        price_manually_set: true,
                    },
                    select: false,
                });
            };
        });
    },
    remove_global_discount_lines: function() {
        var self = this;
        var product  = this.pos.global_discount_product;
        var to_remove = []
        this.get_orderlines().forEach(function(order_line){
            if (order_line.get_product().id === product.id) {
                to_remove.push(order_line);
            }
        })
        to_remove.forEach(function(order_line){
            self.remove_orderline(order_line, false);
        })
    },
    set_global_discount: function(pc) {
        if (pc && pc > 0) {
            this.global_discount = pc;
        } else {
            this.global_discount = false;
        }
        if (this.pos.chrome.screens) {
            this.pos.chrome.screens.products.action_buttons.discount.renderElement();
        }
        this.recompute_global_discount();
    },
    recompute_global_discount: function() {
        var buffer = this.pos.chrome.screens ? this.pos.chrome.screens.products.numpad.state.get("buffer"): false;
        this.remove_global_discount_lines();
        if (this.global_discount) {
            this.add_global_discount_lines();
        }
        if (buffer !== false) {
            this.pos.chrome.screens.products.numpad.state.set({buffer: buffer});
        }
    },
    set_product: function(id){
        if (id === this.pos.global_discount_product) {
            this.product = this.pos.global_discount_product;
        } else {
            _super_order.set_product.call(this, id);
        }
    },
    get_last_orderline: function(){
        if (!this.global_discount){
            return _super_order.get_last_orderline.call(this)
        } else {
            var discount_product_id = this.pos.global_discount_product.id;
            var last_orderline = false;
            this.orderlines.models.reverse().some(function(orderline){
                if (orderline.product.id !== discount_product_id) {
                    last_orderline = orderline;
                    return true;
                }
                return false;
            });
            this.orderlines.models.reverse();
            return last_orderline;
        }
    },
    select_orderline: function(line){
        if (line && line.product.id !== this.pos.global_discount_product.id) {
            _super_order.select_orderline.call(this, line);
        }
    }
})

screens.ScreenWidget.include({
    barcode_product_action: function(code){
        var self = this;
        if (this.pos.global_discount_product.barcode && code.base_code === this.pos.global_discount_product.barcode){
            this.gui.show_popup('number',{
                'title': _t('Discount Percentage'),
                'value': this.pos.get_order().global_discount || this.pos.config.discount_pc,
                'confirm': function(val) {
                    val = Math.max(0,Math.min(100,val));
                    self.pos.get_order().set_global_discount(val);
                },
            });
        } else {
            this._super(code);
        }
    },
    show: function() {
        this._super();
        this.pos.barcode_reader.action_callback['product'] =  _.bind(this.barcode_product_action, this);
    }
});

var DiscountButton = screens.ActionButtonWidget.extend({
    template: 'DiscountButton',
    init: function(parent, options) {
        this._super(parent,options);
        this.pos.bind('change:selectedOrder', function () {
            debugger;
            this.renderElement();
        }, this);
    },
    renderElement: function(){
        var self = this;
        this._super();
        var order = this.pos.get_order()
        if (order && order.global_discount) {
            $('.js_discount').addClass('discount_selected');
        } else {
            $('.js_discount').removeClass('discount_selected');
        }
    },
    button_click: function(){
        var self = this;
        this.gui.show_popup('number',{
            'title': _t('Discount Percentage'),
            'value': this.pos.get_order().global_discount || this.pos.config.discount_pc,
            'confirm': function(val) {
                val = Math.max(0,Math.min(100,val));
                self.pos.get_order().set_global_discount(val);
            },
        });
    },
});

screens.define_action_button({
    'name': 'discount',
    'widget': DiscountButton,
    'condition': function(){
        return this.pos.config.module_pos_discount && this.pos.config.discount_product_id;
    },
});

return {
    DiscountButton: DiscountButton,
}

});
